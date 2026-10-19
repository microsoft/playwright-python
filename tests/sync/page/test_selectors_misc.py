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

"""Port of tests/page/selectors-misc.spec.ts."""

from typing import Any, Callable, List

import pytest

from playwright.sync_api import Error, Page, expect
from tests.server import Server


def test_SE_133_should_work_for_open_shadow_roots(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/deep-shadow.html")
    assert (
        page.eval_on_selector("id=target", "e => e.textContent") == "Hello from root2"
    )
    assert (
        page.eval_on_selector("data-testid=foo", "e => e.textContent")
        == "Hello from root1"
    )
    assert page.eval_on_selector_all("data-testid=foo", "els => els.length") == 3
    assert page.query_selector("id:light=target") is None
    assert page.query_selector("data-testid:light=foo") is None
    assert page.query_selector_all("data-testid:light=foo") == []


def test_SE_134_should_click_on_links_in_shadow_dom(page: Page, server: Server) -> None:
    page.goto(server.PREFIX + "/shadow-dom-link.html")
    assert page.evaluate("() => window.clickCount") == 0
    page.click("#inner-link")
    assert page.evaluate("() => window.clickCount") == 1


def test_SE_135_should_work_with_visible(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert page.query_selector("div:visible") is None

    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("div:visible", timeout=1000)
    assert "1000ms" in exc_info.value.message

    element, _ = sync_gather(
        lambda: page.wait_for_selector("div:visible", state="attached"),
        lambda: page.eval_on_selector(
            "#target2", "div => div.textContent = 'Now visible'"
        ),
    )
    assert element
    assert element.evaluate("e => e.id") == "target2"

    assert page.eval_on_selector("div:visible", "div => div.id") == "target2"


def test_SE_136_should_work_with_visible(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert page.query_selector("div >> visible=true") is None

    with pytest.raises(Error) as exc_info:
        page.wait_for_selector("div >> visible=true", timeout=1000)
    assert "1000ms" in exc_info.value.message

    element, _ = sync_gather(
        lambda: page.wait_for_selector("div >> visible=true", state="attached"),
        lambda: page.eval_on_selector(
            "#target2", "div => div.textContent = 'Now visible'"
        ),
    )
    assert element
    assert element.evaluate("e => e.id") == "target2"

    assert page.eval_on_selector("div >> visible=true", "div => div.id") == "target2"


def test_SE_137_should_work_with_visible_false(page: Page) -> None:
    page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    expect(page.locator("div >> visible=false")).to_have_count(2)
    page.locator("#target2").evaluate("div => div.textContent = 'Now visible'")
    expect(page.locator("div >> visible=false")).to_have_count(1)


def test_SE_138_should_work_with_nth_match(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert page.query_selector(":nth-match(div, 3)") is None
    assert page.eval_on_selector(":nth-match(div, 1)", "e => e.id") == "target1"
    assert page.eval_on_selector(":nth-match(div, 2)", "e => e.id") == "target2"
    assert (
        page.eval_on_selector(":nth-match(section > div, 2)", "e => e.id") == "target2"
    )
    assert (
        page.eval_on_selector(":nth-match(section, div, 2)", "e => e.id") == "target1"
    )
    assert (
        page.eval_on_selector(":nth-match(div, section, 3)", "e => e.id") == "target2"
    )
    assert (
        page.eval_on_selector_all(
            ":is(:nth-match(div, 1), :nth-match(div, 2))", "els => els.length"
        )
        == 2
    )

    with pytest.raises(Error) as exc_info:
        page.query_selector(":nth-match(div, bar, 0)")
    assert (
        '"nth-match" engine expects a one-based index as the last argument'
        in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        page.query_selector(":nth-match(2)")
    assert (
        '"nth-match" engine expects non-empty selector list and an index argument'
        in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        page.query_selector(":nth-match(div, bar, foo)")
    assert (
        '"nth-match" engine expects a one-based index as the last argument'
        in exc_info.value.message
    )

    element, _ = sync_gather(
        lambda: page.wait_for_selector(":nth-match(div, 3)", state="attached"),
        lambda: page.eval_on_selector(
            "section",
            """section => {
              const div = document.createElement('div');
              div.setAttribute('id', 'target3');
              section.appendChild(div);
            }""",
        ),
    )
    assert element
    assert element.evaluate("e => e.id") == "target3"


def test_SE_139_should_work_with_nth(
    page: Page, sync_gather: Callable[..., List[Any]]
) -> None:
    page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert page.query_selector("div >> nth=2") is None
    assert page.eval_on_selector("div >> nth=0", "e => e.id") == "target1"
    assert page.eval_on_selector("div >> nth=1", "e => e.id") == "target2"
    assert page.eval_on_selector("section > div >> nth=1", "e => e.id") == "target2"
    assert page.eval_on_selector("section, div >> nth=1", "e => e.id") == "target1"
    assert page.eval_on_selector("div, section >> nth=2", "e => e.id") == "target2"

    element, _ = sync_gather(
        lambda: page.wait_for_selector("div >> nth=2", state="attached"),
        lambda: page.eval_on_selector(
            "section",
            """section => {
              const div = document.createElement('div');
              div.setAttribute('id', 'target3');
              section.appendChild(div);
            }""",
        ),
    )
    assert element
    assert element.evaluate("e => e.id") == "target3"

    page.set_content(
        """
    <div>
      <div>
        <div>
          <span>hi</span>
          <span>hello</span>
        </div>
      </div>
    </div>
  """
    )
    assert page.locator("div >> div >> span >> nth=1").text_content() == "hello"


def test_SE_140_should_work_with_strict_mode_and_chaining(page: Page) -> None:
    page.set_content(
        """
    <div>
      <div>
        <div>
          <span>hi</span>
        </div>
      </div>
    </div>
  """
    )
    assert page.locator("div >> div >> span").text_content() == "hi"


def test_SE_141_should_work_with_layout_selectors(page: Page) -> None:
    #
    #      +--+  +--+
    #      | 1|  | 2|
    #      +--+  ++-++
    #      | 3|   | 4|
    # +-------+  ++-++
    # |   0   |  | 5|
    # | +--+  +--+--+
    # | | 6|  | 7|
    # | +--+  +--+
    # |       |
    # O-------+
    #         +--+
    #         | 8|
    #         +--++--+
    #             | 9|
    #             +--+
    #

    boxes = [
        # x, y, width, height
        [0, 0, 150, 150],
        [100, 200, 50, 50],
        [200, 200, 50, 50],
        [100, 150, 50, 50],
        [201, 150, 50, 50],
        [200, 100, 50, 50],
        [50, 50, 50, 50],
        [150, 50, 50, 50],
        [150, -51, 50, 50],
        [201, -101, 50, 50],
    ]
    page.set_content(
        '<container style="width: 500px; height: 500px; position: relative;"></container>'
    )
    page.eval_on_selector(
        "container",
        """(container, boxes) => {
          for (let i = 0; i < boxes.length; i++) {
            const div = document.createElement('div');
            div.style.position = 'absolute';
            div.style.overflow = 'hidden';
            div.style.boxSizing = 'border-box';
            div.style.border = '1px solid black';
            div.id = 'id' + i;
            div.textContent = 'id' + i;
            const box = boxes[i];
            div.style.left = box[0] + 'px';
            // Note that top is a flipped y coordinate.
            div.style.top = (250 - box[1] - box[3]) + 'px';
            div.style.width = box[2] + 'px';
            div.style.height = box[3] + 'px';
            container.appendChild(div);
            const span = document.createElement('span');
            span.textContent = '' + i;
            div.appendChild(span);
          }
        }""",
        boxes,
    )

    def id_of(selector: str) -> str:
        return page.eval_on_selector(selector, "e => e.id")

    def ids_of(selector: str) -> str:
        return page.eval_on_selector_all(
            selector, "els => els.map(e => e.id).join(',')"
        )

    assert id_of("div:right-of(#id6)") == "id7"
    assert id_of("div:right-of(#id1)") == "id2"
    assert id_of("div:right-of(#id3)") == "id4"
    assert page.query_selector("div:right-of(#id4)") is None
    assert id_of("div:right-of(#id0)") == "id7"
    assert id_of("div:right-of(#id8)") == "id9"
    assert ids_of("div:right-of(#id3)") == "id4,id2,id5,id7,id8,id9"
    assert ids_of("div:right-of(#id3, 50)") == "id2,id5,id7,id8"
    assert ids_of("div:right-of(#id3, 49)") == "id7,id8"

    assert id_of("div:left-of(#id2)") == "id1"
    assert page.query_selector("div:left-of(#id0)") is None
    assert id_of("div:left-of(#id5)") == "id0"
    assert id_of("div:left-of(#id9)") == "id8"
    assert id_of("div:left-of(#id4)") == "id3"
    assert ids_of("div:left-of(#id5)") == "id0,id7,id3,id1,id6,id8"
    assert ids_of("div:left-of(#id5, 3)") == "id7,id8"

    assert id_of("div:above(#id0)") == "id3"
    assert id_of("div:above(#id5)") == "id4"
    assert id_of("div:above(#id7)") == "id5"
    assert id_of("div:above(#id8)") == "id0"
    assert id_of("div:above(#id9)") == "id8"
    assert page.query_selector("div:above(#id2)") is None
    assert ids_of("div:above(#id5)") == "id4,id2,id3,id1"
    assert ids_of("div:above(#id5, 20)") == "id4,id3"

    assert id_of("div:below(#id4)") == "id5"
    assert id_of("div:below(#id3)") == "id0"
    assert id_of("div:below(#id2)") == "id4"
    assert id_of("div:below(#id6)") == "id8"
    assert id_of("div:below(#id7)") == "id8"
    assert id_of("div:below(#id8)") == "id9"
    assert page.query_selector("div:below(#id9)") is None
    assert ids_of("div:below(#id3)") == "id0,id5,id6,id7,id8,id9"
    assert ids_of("div:below(#id3, 105)") == "id0,id5,id6,id7"

    assert id_of("div:near(#id0)") == "id3"
    assert ids_of("div:near(#id7)") == "id0,id5,id3,id6"
    assert ids_of("div:near(#id0)") == "id3,id6,id7,id8,id1,id5"
    assert ids_of("div:near(#id6)") == "id0,id3,id7"
    assert ids_of("div:near(#id6, 10)") == "id0"
    assert ids_of("div:near(#id0, 100)") == "id3,id6,id7,id8,id1,id5,id4,id2"

    assert ids_of("div:below(#id5):above(#id8)") == "id7,id6"
    assert id_of("div:below(#id5):above(#id8)") == "id7"

    assert ids_of("div:right-of(#id0) + div:above(#id8)") == "id5,id6,id3"

    with pytest.raises(Error) as exc_info:
        page.query_selector(":near(50)")
    assert (
        '"near" engine expects a selector list and optional maximum distance in pixels'
        in exc_info.value.message
    )


def test_SE_142_should_escape_the_scope_with(page: Page) -> None:
    page.set_content("<div><label>Test</label><input id='myinput'></div>")
    assert page.eval_on_selector("label >> xpath=.. >> input", "e => e.id") == "myinput"


def test_SE_143_xpath_should_be_relative(page: Page) -> None:
    page.set_content(
        """
    <span class="find-me" id=target1>1</span>
    <div>
      <span class="find-me" id=target2>2</span>
    </div>
  """
    )
    assert page.eval_on_selector('//*[@class="find-me"]', "e => e.id") == "target1"

    div = page.query_selector("div")
    assert div
    assert div.eval_on_selector('xpath=./*[@class="find-me"]', "e => e.id") == "target2"
    assert (
        div.eval_on_selector('xpath=.//*[@class="find-me"]', "e => e.id") == "target2"
    )
    assert div.eval_on_selector('//*[@class="find-me"]', "e => e.id") == "target2"
    assert div.eval_on_selector('xpath=/*[@class="find-me"]', "e => e.id") == "target2"

    assert (
        page.eval_on_selector('div >> xpath=./*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert (
        page.eval_on_selector('div >> xpath=.//*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert (
        page.eval_on_selector('div >> //*[@class="find-me"]', "e => e.id") == "target2"
    )
    assert (
        page.eval_on_selector('div >> xpath=/*[@class="find-me"]', "e => e.id")
        == "target2"
    )


def test_SE_144_should_work_with_pipe_in_xpath(page: Page, server: Server) -> None:
    page.set_content(
        """
    <span class="find-me" id=t1>1</span>
    <div>
      <span class="find-me" id=t2>2</span>
    </div>
    <div id=t3>3</span>
  """
    )
    assert (
        page.eval_on_selector_all('//*[@id="t1"]|//*[@id="t3"]', "els => els.length")
        == 2
    )

    e1 = page.wait_for_selector('//*[@id="t1"]|//*[@id="t3"]')
    assert e1
    assert e1.evaluate("e => e.id") == "t1"

    e2 = page.wait_for_selector('//*[@id="unknown"]|//*[@id="t2"]')
    assert e2
    assert e2.evaluate("e => e.id") == "t2"

    page.click('//code|//span[@id="t2"]')


def test_SE_145_should_print_original_xpath_in_error(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.locator("//*[contains(@Class, 'foo']").is_visible()
    # Python quotes the locator in the call log with double quotes, so the single
    # quotes are not escaped as in upstream's "//*[contains(@Class, \'foo\']".
    assert "//*[contains(@Class, 'foo']" in exc_info.value.message
    assert ".//*[contains(@Class, 'foo']" not in exc_info.value.message


def test_SE_146_data_testid_on_the_handle_should_be_relative(
    page: Page,
) -> None:
    page.set_content(
        """
    <span data-testid="find-me" id=target1>1</span>
    <div>
      <span data-testid="find-me" id=target2>2</span>
    </div>
  """
    )
    assert page.eval_on_selector("data-testid=find-me", "e => e.id") == "target1"

    div = page.query_selector("div")
    assert div
    assert div.eval_on_selector("data-testid=find-me", "e => e.id") == "target2"
    assert page.eval_on_selector("div >> data-testid=find-me", "e => e.id") == "target2"


def test_SE_147_should_properly_determine_visibility_of_display_contents_elements(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/11202
    page.set_content(
        """
    <div>
      <p style="display:contents">DISPLAY CONTENTS</p>
    </div>"""
    )
    page.wait_for_selector('"DISPLAY CONTENTS"')

    page.set_content(
        """
    <div>
      <article style="display:contents"><div>DISPLAY CONTENTS</div></article>
    </div>"""
    )
    page.wait_for_selector("article")

    page.set_content(
        """
    <div>
      <article style="display:contents"><div style="display:contents">DISPLAY CONTENTS</div></article>
    </div>"""
    )
    page.wait_for_selector("article")

    page.set_content(
        """
    <div>
      <article style="display:contents"><div></div>DISPLAY CONTENTS<span></span></article>
    </div>"""
    )
    page.wait_for_selector("article")

    page.set_content(
        """
    <div>
      <article style="display:contents"><div></div></article>
    </div>"""
    )
    page.wait_for_selector("article", state="hidden")


def test_SE_148_should_work_with_internal_has(page: Page, server: Server) -> None:
    def count(selector: str) -> int:
        return page.eval_on_selector_all(selector, "els => els.length")

    def outer_html(selector: str) -> str:
        return page.eval_on_selector(selector, "e => e.outerHTML")

    page.goto(server.PREFIX + "/deep-shadow.html")
    assert count('div >> internal:has="#target"') == 2
    assert count('div >> internal:has="[data-testid=foo]"') == 3
    assert count('div >> internal:has="[attr*=value]"') == 2

    page.set_content(
        "<section><span></span><div></div></section><section><br></section>"
    )
    assert count('section >> internal:has="span, div"') == 1
    assert count('section >> internal:has="span, div"') == 1
    assert count('section >> internal:has="br"') == 1
    assert count('section >> internal:has="span, br"') == 2
    assert count('section >> internal:has="span, br, div"') == 2

    page.set_content("<div><span>hello</span></div><div><span>world</span></div>")
    assert count('div >> internal:has="text=world"') == 1
    assert (
        outer_html('div >> internal:has="text=world"')
        == "<div><span>world</span></div>"
    )
    assert count('div >> internal:has="text=\\"hello\\""') == 1
    assert (
        outer_html('div >> internal:has="text=\\"hello\\""')
        == "<div><span>hello</span></div>"
    )
    assert count('div >> internal:has="xpath=./span"') == 2
    assert count('div >> internal:has="span"') == 2
    assert count('div >> internal:has="span >> text=wor"') == 1
    assert (
        outer_html('div >> internal:has="span >> text=wor"')
        == "<div><span>world</span></div>"
    )
    assert (
        outer_html('div >> internal:has="span >> text=wor" >> span')
        == "<span>world</span>"
    )

    with pytest.raises(Error) as exc_info:
        page.query_selector("div >> internal:has=abc")
    assert "Malformed selector: internal:has=abc" in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        page.query_selector('internal:has="div"')
    assert '"internal:has" selector cannot be first' in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        page.query_selector("div >> internal:has=33")
    assert "Malformed selector: internal:has=33" in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        page.query_selector('div >> internal:has="span!"')
    assert (
        'Unexpected token "!" while parsing css selector "span!"'
        in exc_info.value.message
    )


def test_SE_149_should_work_with_internal_has_not(page: Page) -> None:
    def count(selector: str) -> int:
        return page.eval_on_selector_all(selector, "els => els.length")

    page.set_content(
        "<section><span></span><div></div></section><section><br></section>"
    )
    assert count('section >> internal:has-not="span"') == 1
    assert count('section >> internal:has-not="span, div, br"') == 0
    assert count('section >> internal:has-not="br"') == 1
    assert count('section >> internal:has-not="span, div"') == 1
    assert count('section >> internal:has-not="article"') == 2


def test_SE_150_should_work_with_internal_and(page: Page, server: Server) -> None:
    def texts(selector: str) -> List[str]:
        return page.eval_on_selector_all(selector, "els => els.map(e => e.textContent)")

    page.set_content(
        """
    <div class=foo>hello</div><div class=bar>world</div>
    <span class=foo>hello2</span><span class=bar>world2</span>
  """
    )
    assert texts('div >> internal:and="span"') == []
    assert texts('div >> internal:and=".foo"') == ["hello"]
    assert texts('div >> internal:and=".bar"') == ["world"]
    assert texts('span >> internal:and="span"') == ["hello2", "world2"]
    assert texts('.foo >> internal:and="div"') == ["hello"]
    assert texts('.bar >> internal:and="span"') == ["world2"]


def test_SE_151_should_work_with_internal_or(page: Page, server: Server) -> None:
    page.set_content(
        """
    <div>hello</div>
    <span>world</span>
  """
    )
    assert page.eval_on_selector_all(
        'div >> internal:or="span"', "els => els.map(e => e.textContent)"
    ) == ["hello", "world"]
    assert page.eval_on_selector_all(
        'span >> internal:or="div"', "els => els.map(e => e.textContent)"
    ) == ["hello", "world"]
    assert (
        page.eval_on_selector_all(
            'article >> internal:or="something"', "els => els.length"
        )
        == 0
    )
    assert page.locator('article >> internal:or="div"').text_content() == "hello"
    assert page.locator('article >> internal:or="span"').text_content() == "world"
    assert page.locator('div >> internal:or="article"').text_content() == "hello"
    assert page.locator('span >> internal:or="article"').text_content() == "world"


def test_SE_152_should_work_with_internal_chain(page: Page, server: Server) -> None:
    page.set_content(
        """
    <div>one <span>two</span> <button>three</button> </div>
    <span>four</span>
    <button>five</button>
  """
    )
    assert page.eval_on_selector_all(
        'div >> internal:chain="button"', "els => els.map(e => e.textContent)"
    ) == ["three"]
    assert page.eval_on_selector_all(
        'div >> internal:chain="span >> internal:or=\\"button\\""',
        "els => els.map(e => e.textContent)",
    ) == ["two", "three"]


def test_SE_153_chaining_should_work_with_large_dom_smoke(
    page: Page, server: Server
) -> None:
    page.evaluate(
        """() => {
          let last = document.body;
          for (let i = 0; i < 100; i++) {
            const e = document.createElement('div');
            last.appendChild(e);
            last = e;
          }
          const target = document.createElement('span');
          target.textContent = 'Found me!';
          last.appendChild(target);
        }"""
    )

    # Naive implementation generates C(100, 9) ~= 1.9*10^12 entries.
    selectors = [
        "div >> div >> div >> div >> div >> div >> div >> div >> span",
        "div div div div div div div div span",
        "div div >> div div >> div div >> div div >> span",
    ]

    counts = []
    for selector in selectors:
        counts.append(page.eval_on_selector_all(selector, "els => els.length"))
    assert counts == [1, 1, 1]
