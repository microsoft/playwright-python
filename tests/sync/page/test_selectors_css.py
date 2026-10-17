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

"""Port of tests/page/selectors-css.spec.ts."""

from typing import List, Union

import pytest

from playwright.sync_api import ElementHandle, Page, expect
from tests.server import Server

NODE_NAMES = "els => els.map(e => e.nodeName).join(',')"
COUNT = "els => els.length"
IDS = "els => els.map(e => e.id)"
TEXTS = "els => els.map(e => e.textContent)"


def test_SE_001_should_work_with_large_dom_smoke(page: Page) -> None:
    page.evaluate(
        """() => {
        let id = 0;
        const next = (tag) => {
          const e = document.createElement(tag);
          const eid = ++id;
          e.textContent = 'id' + eid;
          e.id = '' + eid;
          return e;
        };
        const generate = (depth) => {
          const div = next('div');
          const span1 = next('span');
          const span2 = next('span');
          div.appendChild(span1);
          div.appendChild(span2);
          if (depth > 0) {
            div.appendChild(generate(depth - 1));
            div.appendChild(generate(depth - 1));
          }
          return div;
        };
        document.body.appendChild(generate(12));
      }"""
    )
    selectors = [
        "div div div span",
        "div > div div > span",
        "div + div div div span + span",
        "div ~ div div > span ~ span",
        "div > div > div + div > div + div > span ~ span",
        "div div div div div div div div div div span",
        "div > div > div > div > div > div > div > div > div > div > span",
        "div ~ div div ~ div div ~ div div ~ div div ~ div span",
        "span",
    ]

    for selector in selectors:
        counts1 = [page.eval_on_selector_all(selector, COUNT)]
        counts2 = [
            page.evaluate(
                "selector => document.querySelectorAll(selector).length", selector
            )
        ]
        assert counts1 == counts2


def test_SE_002_should_work_for_open_shadow_roots(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    text = "e => e.textContent"
    assert page.eval_on_selector("css=span", text) == "Hello from root1"
    assert (
        page.eval_on_selector('css=[attr="value\\ space"]', text)
        == "Hello from root3 #2"
    )
    assert (
        page.eval_on_selector("css=[attr='value\\ \\space']", text)
        == "Hello from root3 #2"
    )
    assert page.eval_on_selector("css=div div span", text) == "Hello from root2"
    assert page.eval_on_selector("css=div span + span", text) == "Hello from root3 #2"
    assert (
        page.eval_on_selector('css=span + [attr*="value"]', text)
        == "Hello from root3 #2"
    )
    assert (
        page.eval_on_selector('css=[data-testid="foo"] + [attr*="value"]', text)
        == "Hello from root3 #2"
    )
    assert page.eval_on_selector("css=#target", text) == "Hello from root2"
    assert page.eval_on_selector("css=div #target", text) == "Hello from root2"
    assert page.eval_on_selector("css=div div #target", text) == "Hello from root2"
    assert page.query_selector("css=div div div #target") is None
    assert (
        page.eval_on_selector("css=section > div div span", text) == "Hello from root2"
    )
    assert (
        page.eval_on_selector("css=section > div div span:nth-child(2)", text)
        == "Hello from root3 #2"
    )
    assert page.query_selector("css=section div div div div") is None

    root2 = page.query_selector("css=div div")
    assert root2
    assert root2.eval_on_selector("css=#target", text) == "Hello from root2"
    assert root2.query_selector("css:light=#target") is None
    root2_shadow = (root2.evaluate_handle("r => r.shadowRoot")).as_element()
    assert root2_shadow
    assert (
        root2_shadow.eval_on_selector("css:light=#target", text) == "Hello from root2"
    )
    root3 = (page.query_selector_all("css=div div"))[1]
    assert root3.eval_on_selector("text=root3", text) == "Hello from root3"
    assert root3.eval_on_selector('css=[attr*="value"]', text) == "Hello from root3 #2"
    assert root3.query_selector('css:light=[attr*="value"]') is None


def test_SE_003_should_work_with_combinator_and_spaces(page: Page) -> None:
    page.set_content('<div foo="bar" bar="baz"><span></span></div>')
    for selector in [
        'div[foo="bar"] > span',
        'div[foo="bar"]> span',
        'div[foo="bar"] >span',
        'div[foo="bar"]>span',
        'div[foo="bar"]   >    span',
        'div[foo="bar"]>    span',
        'div[foo="bar"]     >span',
        'div[foo="bar"][bar="baz"] > span',
        'div[foo="bar"][bar="baz"]> span',
        'div[foo="bar"][bar="baz"] >span',
        'div[foo="bar"][bar="baz"]>span',
        'div[foo="bar"][bar="baz"]   >    span',
        'div[foo="bar"][bar="baz"]>    span',
        'div[foo="bar"][bar="baz"]     >span',
    ]:
        assert page.eval_on_selector(selector, "e => e.outerHTML") == "<span></span>"


def test_SE_004_should_work_with_comma_separated_list(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert page.eval_on_selector_all("css=span,section #root1", COUNT) == 5
    assert page.eval_on_selector_all("css=section #root1, div span", COUNT) == 5
    assert (
        page.eval_on_selector("css=doesnotexist , section #root1", "e => e.id")
        == "root1"
    )
    assert page.eval_on_selector_all("css=doesnotexist ,section #root1", COUNT) == 1
    assert page.eval_on_selector_all("css=span,div span", COUNT) == 4
    assert page.eval_on_selector_all("css=span,div span,div div span", COUNT) == 4
    assert page.eval_on_selector_all('css=#target,[attr="value\\ space"]', COUNT) == 2
    assert (
        page.eval_on_selector_all(
            'css=#target,[data-testid="foo"],[attr="value\\ space"]', COUNT
        )
        == 4
    )
    assert (
        page.eval_on_selector_all(
            'css=#target,[data-testid="foo"],[attr="value\\ space"],span', COUNT
        )
        == 4
    )


def test_SE_005_should_keep_dom_order_with_comma_separated_list(
    page: Page,
) -> None:
    page.set_content("<section><span><div><x></x><y></y></div></span></section>")
    assert page.eval_on_selector_all("css=span,div", NODE_NAMES) == "SPAN,DIV"
    assert page.eval_on_selector_all("css=div,span", NODE_NAMES) == "SPAN,DIV"
    assert page.eval_on_selector_all("css=span div, div", NODE_NAMES) == "DIV"
    assert (
        page.eval_on_selector_all("*css=section >> css=div,span", NODE_NAMES)
        == "SECTION"
    )
    assert (
        page.eval_on_selector_all("css=section >> *css=div >> css=x,y", NODE_NAMES)
        == "DIV"
    )
    assert (
        page.eval_on_selector_all("css=section >> *css=div,span >> css=x,y", NODE_NAMES)
        == "SPAN,DIV"
    )
    assert (
        page.eval_on_selector_all("css=section >> *css=div,span >> css=y", NODE_NAMES)
        == "SPAN,DIV"
    )


def test_SE_006_should_return_multiple_captures_for_the_same_node(
    page: Page,
) -> None:
    page.set_content("<div><div><div><span></span></div></div></div>")
    assert page.eval_on_selector_all("*css=div >> span", NODE_NAMES) == ("DIV,DIV,DIV")


def test_SE_007_should_return_multiple_captures_when_going_up_the_hierarchy(
    page: Page,
) -> None:
    page.set_content("<section>Hello<ul><li></li><li></li></ul></section>")
    assert (
        page.eval_on_selector_all("*css=li >> ../.. >> text=Hello", NODE_NAMES)
        == "LI,LI"
    )


def test_SE_008_should_work_with_comma_separated_list_in_various_positions(
    page: Page,
) -> None:
    page.set_content("<section><span><div><x></x><y></y></div></span></section>")
    assert page.eval_on_selector_all("css=span,div >> css=x,y", NODE_NAMES) == ("X,Y")
    assert page.eval_on_selector_all("css=span,div >> css=x", NODE_NAMES) == "X"
    assert page.eval_on_selector_all("css=div >> css=x,y", NODE_NAMES) == "X,Y"
    assert page.eval_on_selector_all("css=div >> css=x", NODE_NAMES) == "X"

    assert (
        page.eval_on_selector_all("css=section >> css=div >> css=x", NODE_NAMES) == "X"
    )
    assert (
        page.eval_on_selector_all(
            "css=section >> css=span >> css=div >> css=y", NODE_NAMES
        )
        == "Y"
    )
    assert (
        page.eval_on_selector_all("css=section >> css=div >> css=x,y", NODE_NAMES)
        == "X,Y"
    )
    assert (
        page.eval_on_selector_all("css=section >> css=div,span >> css=x,y", NODE_NAMES)
        == "X,Y"
    )
    assert (
        page.eval_on_selector_all("css=section >> css=span >> css=x,y", NODE_NAMES)
        == "X,Y"
    )


def test_SE_009_should_work_with_comma_inside_text(page: Page) -> None:
    page.set_content('<span></span><div attr="hello,world!"></div>')
    outer = "e => e.outerHTML"
    assert (
        page.eval_on_selector('css=div[attr="hello,world!"]', outer)
        == '<div attr="hello,world!"></div>'
    )
    assert (
        page.eval_on_selector('css=[attr="hello,world!"]', outer)
        == '<div attr="hello,world!"></div>'
    )
    assert (
        page.eval_on_selector("css=div[attr='hello,world!']", outer)
        == '<div attr="hello,world!"></div>'
    )
    assert (
        page.eval_on_selector("css=[attr='hello,world!']", outer)
        == '<div attr="hello,world!"></div>'
    )
    assert (
        page.eval_on_selector('css=div[attr="hello,world!"],span', outer)
        == "<span></span>"
    )


def test_SE_010_should_work_with_attribute_selectors(page: Page) -> None:
    page.set_content(
        """<div attr="hello world" attr2="hello-''>>foo=bar[]" attr3="] span"><span></span></div>"""
    )
    page.evaluate("() => window['div'] = document.querySelector('div')")
    selectors = [
        '[attr="hello world"]',
        '[attr = "hello world"]',
        "[attr ~= world]",
        "[attr ^=hello ]",
        "[attr $= world ]",
        '[attr *= "llo wor" ]',
        "[attr2 |= hello]",
        '[attr = "Hello World" i ]',
        '[attr *= "llo WOR"i]',
        "[attr $= woRLD i]",
        """[attr2 = "hello-''>>foo=bar[]"]""",
        '[attr2 $="foo=bar[]"]',
    ]
    for selector in selectors:
        assert page.eval_on_selector(selector, "e => e === window['div']") is True
    assert (
        page.eval_on_selector(
            "[attr*=hello] span", "e => e.parentNode === window['div']"
        )
        is True
    )
    assert (
        page.eval_on_selector(
            "[attr*=hello] >> span", "e => e.parentNode === window['div']"
        )
        is True
    )
    assert (
        page.eval_on_selector(
            '[attr3="] span"] >> span', "e => e.parentNode === window['div']"
        )
        is True
    )


def test_SE_011_should_not_match_root_after(page: Page) -> None:
    page.set_content("<section><div>test</div></section>")
    element = page.query_selector("css=section >> css=section")
    assert element is None


def test_SE_012_should_work_with_numerical_id(page: Page) -> None:
    page.set_content('<section id="123"></section>')
    element = page.query_selector("#\\31\\32\\33")
    assert element


def test_SE_013_should_work_with_wrong_case_id(page: Page) -> None:
    page.set_content('<section id="Hello"></section>')
    assert page.eval_on_selector("#Hello", "e => e.tagName") == "SECTION"
    assert page.eval_on_selector("#hello", "e => e.tagName") == "SECTION"
    assert page.eval_on_selector("#HELLO", "e => e.tagName") == "SECTION"
    assert page.eval_on_selector("#helLO", "e => e.tagName") == "SECTION"


def test_SE_014_should_work_with(page: Page) -> None:
    page.set_content("<div id=div1></div><div id=div2><span><span></span></span></div>")
    # Includes html, head and body.
    assert page.eval_on_selector_all("*", COUNT) == 7
    assert page.eval_on_selector_all("*#div1", COUNT) == 1
    assert page.eval_on_selector_all("*:not(#div1)", COUNT) == 6
    assert page.eval_on_selector_all("*:not(div)", COUNT) == 5
    assert page.eval_on_selector_all("*:not(span)", COUNT) == 5
    assert page.eval_on_selector_all("*:not(*)", COUNT) == 0
    assert page.eval_on_selector_all("*:is(*)", COUNT) == 7
    assert page.eval_on_selector_all("* *", COUNT) == 6
    assert page.eval_on_selector_all("* *:not(span)", COUNT) == 4
    assert page.eval_on_selector_all("div > *", COUNT) == 1
    assert page.eval_on_selector_all("div *", COUNT) == 2
    assert page.eval_on_selector_all("* > *", COUNT) == 6

    body = page.query_selector("body")
    assert body
    # Does not include html, head or body.
    assert body.eval_on_selector_all("*", COUNT) == 4
    assert body.eval_on_selector_all("*#div1", COUNT) == 1
    assert body.eval_on_selector_all("*:not(#div1)", COUNT) == 3
    assert body.eval_on_selector_all("*:not(div)", COUNT) == 2
    assert body.eval_on_selector_all("*:not(span)", COUNT) == 2
    assert body.eval_on_selector_all("*:not(*)", COUNT) == 0
    assert body.eval_on_selector_all("*:is(*)", COUNT) == 4
    assert body.eval_on_selector_all("div > *", COUNT) == 1
    assert body.eval_on_selector_all("div *", COUNT) == 2
    # Selectors v2 matches jquery in the sense that matching starts with the element scope,
    # not the document scope.
    assert body.eval_on_selector_all("* > *", COUNT) == 2
    # Adding scope makes querySelectorAll work like jquery.
    assert body.eval_on_selector_all(":scope * > *", COUNT) == 2
    # Note that the following two selectors are following jquery logic even
    # with selectors v1. Just running `body.querySelectorAll` returns 4 and 2 respectively.
    # That's probably a bug in v1, but oh well.
    assert body.eval_on_selector_all("* *", COUNT) == 2
    assert body.eval_on_selector_all("* *:not(span)", COUNT) == 0


def test_SE_015_should_work_with_nth_child(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert page.eval_on_selector_all("css=span:nth-child(odd)", COUNT) == 3
    assert page.eval_on_selector_all("css=span:nth-child(even)", COUNT) == 1
    assert page.eval_on_selector_all("css=span:nth-child(n+1)", COUNT) == 4
    assert page.eval_on_selector_all("css=span:nth-child(n+2)", COUNT) == 1
    assert page.eval_on_selector_all("css=span:nth-child(2n)", COUNT) == 1
    assert page.eval_on_selector_all("css=span:nth-child(2n+1)", COUNT) == 3
    assert page.eval_on_selector_all("css=span:nth-child(-n)", COUNT) == 0
    assert page.eval_on_selector_all("css=span:nth-child(-n+1)", COUNT) == 3
    assert page.eval_on_selector_all("css=span:nth-child(-n+2)", COUNT) == 4
    assert page.eval_on_selector_all("css=span:nth-child(23n+2)", COUNT) == 1


def test_SE_016_should_work_with_nth_child_of_notation_with_nested_functions(
    page: Page, browser_name: str, browser_major_version: int
) -> None:
    if browser_name == "chromium" and browser_major_version < 111:
        pytest.skip("https://caniuse.com/css-nth-child-of")

    page.set_content(
        """
    <div>
      <span>span1</span>
      <span class=foo>span2<dd></dd></span>
      <span class=foo>span3<dd class=marker></dd></span>
      <span class=foo>span4<dd class=marker></dd></span>
      <span class=foo>span5<dd></dd></span>
      <span>span6</span>
    </div>
  """
    )
    assert page.eval_on_selector_all("css=span:nth-child(1)", TEXTS) == ["span1"]
    assert page.eval_on_selector_all("css=span:nth-child(1 of .foo)", TEXTS) == [
        "span2"
    ]
    assert page.eval_on_selector_all(
        "css=span:nth-child(1 of .foo:has(dd.marker))", TEXTS
    ) == ["span3"]
    assert page.eval_on_selector_all(
        "css=span:nth-last-child(1 of .foo:has(dd.marker))", TEXTS
    ) == ["span4"]
    assert page.eval_on_selector_all("css=span:nth-last-child(1 of .foo)", TEXTS) == [
        "span5"
    ]
    assert page.eval_on_selector_all("css=span:nth-last-child(  1  )", TEXTS) == [
        "span6"
    ]

    assert page.eval_on_selector_all(
        "css=span:nth-child(1 of .foo:nth-child(3))", TEXTS
    ) == ["span3"]
    assert (
        page.eval_on_selector_all("css=span:nth-child(1 of .foo:nth-child(6))", TEXTS)
        == []
    )


def test_SE_017_should_work_with_not(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert page.eval_on_selector_all("css=div:not(#root1)", COUNT) == 2
    assert page.eval_on_selector_all("css=body :not(span)", COUNT) == 4
    assert page.eval_on_selector_all("css=div > :not(span):not(div)", COUNT) == 0


def test_SE_018_should_work_with(page: Page) -> None:
    page.set_content(
        """
    <div id=div1></div>
    <div id=div2></div>
    <div id=div3></div>
    <div id=div4></div>
    <div id=div5></div>
    <div id=div6></div>
  """
    )
    assert page.eval_on_selector_all("#div3 >> :scope ~ div", IDS) == [
        "div4",
        "div5",
        "div6",
    ]
    assert page.eval_on_selector_all("#div3 >> :scope ~ *", IDS) == [
        "div4",
        "div5",
        "div6",
    ]
    assert page.eval_on_selector_all("#div3 >> ~ div", IDS) == [
        "div4",
        "div5",
        "div6",
    ]
    assert page.eval_on_selector_all("#div3 >> ~ *", IDS) == [
        "div4",
        "div5",
        "div6",
    ]
    assert page.eval_on_selector_all("#div3 >> #div1 ~ :scope", IDS) == ["div3"]
    assert page.eval_on_selector_all("#div3 >> #div4 ~ :scope", IDS) == []
    assert page.eval_on_selector_all("css=#div1 ~ div ~ #div6", COUNT) == 1
    assert page.eval_on_selector_all("css=#div1 ~ div ~ div", COUNT) == 4
    assert page.eval_on_selector_all("css=#div3 ~ div ~ div", COUNT) == 2
    assert page.eval_on_selector_all("css=#div4 ~ div ~ div", COUNT) == 1
    assert page.eval_on_selector_all("css=#div5 ~ div ~ div", COUNT) == 0
    assert page.eval_on_selector_all("css=#div3 ~ #div2 ~ #div6", COUNT) == 0
    assert page.eval_on_selector_all("css=#div3 ~ #div4 ~ #div5", COUNT) == 1


def test_SE_019_should_work_with(page: Page) -> None:
    page.set_content(
        """
    <section>
      <div id=div1></div>
      <div id=div2></div>
      <div id=div3></div>
      <div id=div4></div>
      <div id=div5></div>
      <div id=div6></div>
    </section>
  """
    )
    assert page.eval_on_selector_all("#div1 >> :scope+div", IDS) == ["div2"]
    assert page.eval_on_selector_all("#div1 >> :scope+*", IDS) == ["div2"]
    assert page.eval_on_selector_all("#div1 >> + div", IDS) == ["div2"]
    assert page.eval_on_selector_all("#div1 >> + *", IDS) == ["div2"]
    assert page.eval_on_selector_all("#div3 >> div + :scope", IDS) == ["div3"]
    assert page.eval_on_selector_all("#div3 >> #div1 + :scope", IDS) == []
    assert page.eval_on_selector_all("css=#div1 ~ div + #div6", COUNT) == 1
    assert page.eval_on_selector_all("css=#div1 ~ div + div", COUNT) == 4
    assert page.eval_on_selector_all("css=#div3 + div + div", COUNT) == 1
    assert page.eval_on_selector_all("css=#div4 ~ #div5 + div", COUNT) == 1
    assert page.eval_on_selector_all("css=#div5 + div + div", COUNT) == 0
    assert page.eval_on_selector_all("css=#div3 ~ #div2 + #div6", COUNT) == 0
    assert page.eval_on_selector_all("css=#div3 + #div4 + #div5", COUNT) == 1
    assert page.eval_on_selector_all("css=div + #div1", COUNT) == 0
    assert page.eval_on_selector_all("css=section > div + div ~ div", COUNT) == 4
    assert page.eval_on_selector_all("css=section > div + #div4 ~ div", COUNT) == 2
    assert (
        page.eval_on_selector_all("css=section:has(:scope > div + #div2)", COUNT) == 1
    )
    assert (
        page.eval_on_selector_all("css=section:has(:scope > div + #div1)", COUNT) == 0
    )
    assert page.eval_on_selector("css=div:has(:scope + #div5)", "e => e.id") == "div4"


def test_SE_020_should_work_with_spaces_in_nth_child_and_not(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert page.eval_on_selector_all("css=span:nth-child(23n +2)", COUNT) == 1
    assert page.eval_on_selector_all("css=span:nth-child(23n+ 2)", COUNT) == 1
    assert page.eval_on_selector_all("css=span:nth-child( 23n + 2 )", COUNT) == 1
    assert page.eval_on_selector_all("css=span:not(#root1 #target)", COUNT) == 3
    assert page.eval_on_selector_all("css=span:not(:not(#root1 #target))", COUNT) == 1
    assert (
        page.eval_on_selector_all("css=span:not(span:not(#root1 #target))", COUNT) == 1
    )
    assert page.eval_on_selector_all("css=div > :not(span)", COUNT) == 2
    assert page.eval_on_selector_all("css=body :not(span, div)", COUNT) == 1
    assert page.eval_on_selector_all("css=span, section:not(span, div)", COUNT) == 5
    assert page.eval_on_selector_all("span:nth-child(23n+ 2) >> xpath=.", COUNT) == 1


def test_SE_021_should_work_with_is(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert page.eval_on_selector_all("css=div:is(#root1)", COUNT) == 1
    assert page.eval_on_selector_all("css=div:is(#root1, #target)", COUNT) == 1
    assert page.eval_on_selector_all("css=div:is(span, #target)", COUNT) == 0
    assert page.eval_on_selector_all("css=div:is(span, #root1 > *)", COUNT) == 2
    assert page.eval_on_selector_all("css=div:is(section div)", COUNT) == 3
    assert page.eval_on_selector_all("css=:is(div, span)", COUNT) == 7
    assert (
        page.eval_on_selector_all("css=section:is(section) div:is(section div)", COUNT)
        == 3
    )
    assert page.eval_on_selector_all("css=:is(div, span) > *", COUNT) == 6
    assert page.eval_on_selector_all("css=#root1:has(:is(#root1))", COUNT) == 0
    assert page.eval_on_selector_all("css=#root1:has(:is(:scope, #root1))", COUNT) == 1


def test_SE_022_should_work_with_has(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert page.eval_on_selector_all("css=div:has(#target)", COUNT) == 2
    assert page.eval_on_selector_all("css=div:has([data-testid=foo])", COUNT) == 3
    assert page.eval_on_selector_all("css=div:has([attr*=value])", COUNT) == 2

    page.set_content(
        "<section><span></span><div></div></section><section><br></section>"
    )
    assert page.eval_on_selector_all("section:has(span, div)", COUNT) == 1
    assert page.eval_on_selector_all("section:has(span, div)", COUNT) == 1
    assert page.eval_on_selector_all("section:has(br)", COUNT) == 1
    assert page.eval_on_selector_all("section:has(span, br)", COUNT) == 2
    assert page.eval_on_selector_all("section:has(span, br, div)", COUNT) == 2


def test_SE_023_should_work_with_scope(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    # 'is' does not change the scope, so it remains 'html'.
    assert page.eval_on_selector_all("css=div:is(:scope#root1)", COUNT) == 0
    assert page.eval_on_selector_all("css=div:is(:scope #root1)", COUNT) == 1
    # 'has' does change the scope, so it becomes the 'div' we are querying.
    assert page.eval_on_selector_all("css=div:has(:scope > #target)", COUNT) == 1

    handle = page.query_selector("css=span")
    assert handle
    scopes: List[Union[Page, ElementHandle]] = [page, handle]
    for scope in scopes:
        assert scope.eval_on_selector_all("css=:scope", COUNT) == 1
        assert scope.eval_on_selector_all("css=* :scope", COUNT) == 0
        assert scope.eval_on_selector_all("css=* + :scope", COUNT) == 0
        assert scope.eval_on_selector_all("css=* > :scope", COUNT) == 0
        assert scope.eval_on_selector_all("css=* ~ :scope", COUNT) == 0

    page.set_content("<article><div class=target>hello<span></span></div></article>")
    # 'scope' should allow additional native css modifiers
    text = "e => e.textContent"
    assert page.eval_on_selector("div >> :scope.target", text) == "hello"
    assert page.eval_on_selector("div >> :scope:nth-child(1)", text) == "hello"
    assert page.eval_on_selector("div >> :scope.target:has(span)", text) == ("hello")
    assert page.eval_on_selector("html:scope", "e => e.nodeName") == "HTML"

    page.set_content(
        "<section><span id=span1><span id=inner></span></span><span id=span2></span></section>"
    )
    assert page.eval_on_selector_all("#span1 >> span:not(:has(:scope > div))", IDS) == [
        "inner"
    ]
    assert page.eval_on_selector_all("#span1 >> #inner,:scope", IDS) == [
        "span1",
        "inner",
    ]
    assert page.eval_on_selector_all("#span1 >> span,:scope", IDS) == [
        "span1",
        "inner",
    ]
    assert page.eval_on_selector_all("#span1 >> span:not(:scope)", IDS) == ["inner"]
    # TODO: the following two do not work. We do not expand the context for the inner :scope,
    # because we should only expand for one clause of :is() that contains :scope, but not the other.
    # assert page.eval_on_selector_all("#span1 >> span:is(:scope)", IDS) == ["span1"]
    # assert page.eval_on_selector_all("#span1 >> span:is(:scope,#inner)", IDS) == ["span1", "inner"]


def test_SE_024_should_work_with_scope_and_class(page: Page) -> None:
    page.set_content(
        """<div class="apple"></div>
                         <div class="apple selected"></div>"""
    )
    apples = page.locator(".apple")
    selected_apples = apples.locator(":scope.selected")
    expect(selected_apples).to_have_count(1)


def test_SE_025_should_absolutize_relative_selectors(page: Page) -> None:
    page.set_content("<div><span>Hi</span></div>")
    assert page.eval_on_selector("div >> >span", "e => e.textContent") == "Hi"
    assert page.locator("div").locator(">span").text_content() == "Hi"
    assert (
        page.eval_on_selector("div:has(> span)", "e => e.outerHTML")
        == "<div><span>Hi</span></div>"
    )
    assert page.query_selector("div:has(> div)") is None


def test_SE_026_css_on_the_handle_should_be_relative(page: Page) -> None:
    page.set_content(
        """
    <span class="find-me" id=target1>1</span>
    <div>
      <span class="find-me" id=target2>2</span>
    </div>
  """
    )
    assert page.eval_on_selector(".find-me", "e => e.id") == "target1"

    div = page.query_selector("div")
    assert div
    assert div.eval_on_selector(".find-me", "e => e.id") == "target2"
    assert page.eval_on_selector("div >> .find-me", "e => e.id") == "target2"


def test_SE_027_should_use_light_dom_structure_for_child_combinator_with_slotted_content(
    page: Page,
) -> None:
    page.set_content(
        """
    <my-button>
      <template shadowrootmode="open">
        <button><slot></slot></button>
      </template>
      <div class="content">Foo</div>
    </my-button>
  """
    )
    assert page.eval_on_selector("my-button > div", "e => e.className") == ("content")
    assert page.eval_on_selector("my-button > .content", "e => e.textContent") == (
        "Foo"
    )
