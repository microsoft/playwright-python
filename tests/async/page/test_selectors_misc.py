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

import asyncio
from typing import List

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server


async def test_SE_133_should_work_for_open_shadow_roots(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/deep-shadow.html")
    assert (
        await page.eval_on_selector("id=target", "e => e.textContent")
        == "Hello from root2"
    )
    assert (
        await page.eval_on_selector("data-testid=foo", "e => e.textContent")
        == "Hello from root1"
    )
    assert await page.eval_on_selector_all("data-testid=foo", "els => els.length") == 3
    assert await page.query_selector("id:light=target") is None
    assert await page.query_selector("data-testid:light=foo") is None
    assert await page.query_selector_all("data-testid:light=foo") == []


async def test_SE_134_should_click_on_links_in_shadow_dom(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/shadow-dom-link.html")
    assert await page.evaluate("() => window.clickCount") == 0
    await page.click("#inner-link")
    assert await page.evaluate("() => window.clickCount") == 1


async def test_SE_135_should_work_with_visible(page: Page) -> None:
    await page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert await page.query_selector("div:visible") is None

    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("div:visible", timeout=1000)
    assert "1000ms" in exc_info.value.message

    element, _ = await asyncio.gather(
        page.wait_for_selector("div:visible", state="attached"),
        page.eval_on_selector("#target2", "div => div.textContent = 'Now visible'"),
    )
    assert element
    assert await element.evaluate("e => e.id") == "target2"

    assert await page.eval_on_selector("div:visible", "div => div.id") == "target2"


async def test_SE_136_should_work_with_visible(page: Page) -> None:
    await page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert await page.query_selector("div >> visible=true") is None

    with pytest.raises(Error) as exc_info:
        await page.wait_for_selector("div >> visible=true", timeout=1000)
    assert "1000ms" in exc_info.value.message

    element, _ = await asyncio.gather(
        page.wait_for_selector("div >> visible=true", state="attached"),
        page.eval_on_selector("#target2", "div => div.textContent = 'Now visible'"),
    )
    assert element
    assert await element.evaluate("e => e.id") == "target2"

    assert (
        await page.eval_on_selector("div >> visible=true", "div => div.id") == "target2"
    )


async def test_SE_137_should_work_with_visible_false(page: Page) -> None:
    await page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    await expect(page.locator("div >> visible=false")).to_have_count(2)
    await page.locator("#target2").evaluate("div => div.textContent = 'Now visible'")
    await expect(page.locator("div >> visible=false")).to_have_count(1)


async def test_SE_138_should_work_with_nth_match(page: Page) -> None:
    await page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert await page.query_selector(":nth-match(div, 3)") is None
    assert await page.eval_on_selector(":nth-match(div, 1)", "e => e.id") == "target1"
    assert await page.eval_on_selector(":nth-match(div, 2)", "e => e.id") == "target2"
    assert (
        await page.eval_on_selector(":nth-match(section > div, 2)", "e => e.id")
        == "target2"
    )
    assert (
        await page.eval_on_selector(":nth-match(section, div, 2)", "e => e.id")
        == "target1"
    )
    assert (
        await page.eval_on_selector(":nth-match(div, section, 3)", "e => e.id")
        == "target2"
    )
    assert (
        await page.eval_on_selector_all(
            ":is(:nth-match(div, 1), :nth-match(div, 2))", "els => els.length"
        )
        == 2
    )

    with pytest.raises(Error) as exc_info:
        await page.query_selector(":nth-match(div, bar, 0)")
    assert (
        '"nth-match" engine expects a one-based index as the last argument'
        in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        await page.query_selector(":nth-match(2)")
    assert (
        '"nth-match" engine expects non-empty selector list and an index argument'
        in exc_info.value.message
    )

    with pytest.raises(Error) as exc_info:
        await page.query_selector(":nth-match(div, bar, foo)")
    assert (
        '"nth-match" engine expects a one-based index as the last argument'
        in exc_info.value.message
    )

    element, _ = await asyncio.gather(
        page.wait_for_selector(":nth-match(div, 3)", state="attached"),
        page.eval_on_selector(
            "section",
            """section => {
              const div = document.createElement('div');
              div.setAttribute('id', 'target3');
              section.appendChild(div);
            }""",
        ),
    )
    assert element
    assert await element.evaluate("e => e.id") == "target3"


async def test_SE_139_should_work_with_nth(page: Page) -> None:
    await page.set_content(
        """
    <section>
      <div id=target1></div>
      <div id=target2></div>
    </section>
  """
    )
    assert await page.query_selector("div >> nth=2") is None
    assert await page.eval_on_selector("div >> nth=0", "e => e.id") == "target1"
    assert await page.eval_on_selector("div >> nth=1", "e => e.id") == "target2"
    assert (
        await page.eval_on_selector("section > div >> nth=1", "e => e.id") == "target2"
    )
    assert (
        await page.eval_on_selector("section, div >> nth=1", "e => e.id") == "target1"
    )
    assert (
        await page.eval_on_selector("div, section >> nth=2", "e => e.id") == "target2"
    )

    element, _ = await asyncio.gather(
        page.wait_for_selector("div >> nth=2", state="attached"),
        page.eval_on_selector(
            "section",
            """section => {
              const div = document.createElement('div');
              div.setAttribute('id', 'target3');
              section.appendChild(div);
            }""",
        ),
    )
    assert element
    assert await element.evaluate("e => e.id") == "target3"

    await page.set_content(
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
    assert await page.locator("div >> div >> span >> nth=1").text_content() == "hello"


async def test_SE_140_should_work_with_strict_mode_and_chaining(page: Page) -> None:
    await page.set_content(
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
    assert await page.locator("div >> div >> span").text_content() == "hi"


async def test_SE_141_should_work_with_layout_selectors(page: Page) -> None:
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
    await page.set_content(
        '<container style="width: 500px; height: 500px; position: relative;"></container>'
    )
    await page.eval_on_selector(
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

    async def id_of(selector: str) -> str:
        return await page.eval_on_selector(selector, "e => e.id")

    async def ids_of(selector: str) -> str:
        return await page.eval_on_selector_all(
            selector, "els => els.map(e => e.id).join(',')"
        )

    assert await id_of("div:right-of(#id6)") == "id7"
    assert await id_of("div:right-of(#id1)") == "id2"
    assert await id_of("div:right-of(#id3)") == "id4"
    assert await page.query_selector("div:right-of(#id4)") is None
    assert await id_of("div:right-of(#id0)") == "id7"
    assert await id_of("div:right-of(#id8)") == "id9"
    assert await ids_of("div:right-of(#id3)") == "id4,id2,id5,id7,id8,id9"
    assert await ids_of("div:right-of(#id3, 50)") == "id2,id5,id7,id8"
    assert await ids_of("div:right-of(#id3, 49)") == "id7,id8"

    assert await id_of("div:left-of(#id2)") == "id1"
    assert await page.query_selector("div:left-of(#id0)") is None
    assert await id_of("div:left-of(#id5)") == "id0"
    assert await id_of("div:left-of(#id9)") == "id8"
    assert await id_of("div:left-of(#id4)") == "id3"
    assert await ids_of("div:left-of(#id5)") == "id0,id7,id3,id1,id6,id8"
    assert await ids_of("div:left-of(#id5, 3)") == "id7,id8"

    assert await id_of("div:above(#id0)") == "id3"
    assert await id_of("div:above(#id5)") == "id4"
    assert await id_of("div:above(#id7)") == "id5"
    assert await id_of("div:above(#id8)") == "id0"
    assert await id_of("div:above(#id9)") == "id8"
    assert await page.query_selector("div:above(#id2)") is None
    assert await ids_of("div:above(#id5)") == "id4,id2,id3,id1"
    assert await ids_of("div:above(#id5, 20)") == "id4,id3"

    assert await id_of("div:below(#id4)") == "id5"
    assert await id_of("div:below(#id3)") == "id0"
    assert await id_of("div:below(#id2)") == "id4"
    assert await id_of("div:below(#id6)") == "id8"
    assert await id_of("div:below(#id7)") == "id8"
    assert await id_of("div:below(#id8)") == "id9"
    assert await page.query_selector("div:below(#id9)") is None
    assert await ids_of("div:below(#id3)") == "id0,id5,id6,id7,id8,id9"
    assert await ids_of("div:below(#id3, 105)") == "id0,id5,id6,id7"

    assert await id_of("div:near(#id0)") == "id3"
    assert await ids_of("div:near(#id7)") == "id0,id5,id3,id6"
    assert await ids_of("div:near(#id0)") == "id3,id6,id7,id8,id1,id5"
    assert await ids_of("div:near(#id6)") == "id0,id3,id7"
    assert await ids_of("div:near(#id6, 10)") == "id0"
    assert await ids_of("div:near(#id0, 100)") == "id3,id6,id7,id8,id1,id5,id4,id2"

    assert await ids_of("div:below(#id5):above(#id8)") == "id7,id6"
    assert await id_of("div:below(#id5):above(#id8)") == "id7"

    assert await ids_of("div:right-of(#id0) + div:above(#id8)") == "id5,id6,id3"

    with pytest.raises(Error) as exc_info:
        await page.query_selector(":near(50)")
    assert (
        '"near" engine expects a selector list and optional maximum distance in pixels'
        in exc_info.value.message
    )


async def test_SE_142_should_escape_the_scope_with(page: Page) -> None:
    await page.set_content("<div><label>Test</label><input id='myinput'></div>")
    assert (
        await page.eval_on_selector("label >> xpath=.. >> input", "e => e.id")
        == "myinput"
    )


async def test_SE_143_xpath_should_be_relative(page: Page) -> None:
    await page.set_content(
        """
    <span class="find-me" id=target1>1</span>
    <div>
      <span class="find-me" id=target2>2</span>
    </div>
  """
    )
    assert (
        await page.eval_on_selector('//*[@class="find-me"]', "e => e.id") == "target1"
    )

    div = await page.query_selector("div")
    assert div
    assert (
        await div.eval_on_selector('xpath=./*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert (
        await div.eval_on_selector('xpath=.//*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert await div.eval_on_selector('//*[@class="find-me"]', "e => e.id") == "target2"
    assert (
        await div.eval_on_selector('xpath=/*[@class="find-me"]', "e => e.id")
        == "target2"
    )

    assert (
        await page.eval_on_selector('div >> xpath=./*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert (
        await page.eval_on_selector('div >> xpath=.//*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert (
        await page.eval_on_selector('div >> //*[@class="find-me"]', "e => e.id")
        == "target2"
    )
    assert (
        await page.eval_on_selector('div >> xpath=/*[@class="find-me"]', "e => e.id")
        == "target2"
    )


async def test_SE_144_should_work_with_pipe_in_xpath(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
    <span class="find-me" id=t1>1</span>
    <div>
      <span class="find-me" id=t2>2</span>
    </div>
    <div id=t3>3</span>
  """
    )
    assert (
        await page.eval_on_selector_all(
            '//*[@id="t1"]|//*[@id="t3"]', "els => els.length"
        )
        == 2
    )

    e1 = await page.wait_for_selector('//*[@id="t1"]|//*[@id="t3"]')
    assert e1
    assert await e1.evaluate("e => e.id") == "t1"

    e2 = await page.wait_for_selector('//*[@id="unknown"]|//*[@id="t2"]')
    assert e2
    assert await e2.evaluate("e => e.id") == "t2"

    await page.click('//code|//span[@id="t2"]')


async def test_SE_145_should_print_original_xpath_in_error(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        await page.locator("//*[contains(@Class, 'foo']").is_visible()
    # Python quotes the locator in the call log with double quotes, so the single
    # quotes are not escaped as in upstream's "//*[contains(@Class, \'foo\']".
    assert "//*[contains(@Class, 'foo']" in exc_info.value.message
    assert ".//*[contains(@Class, 'foo']" not in exc_info.value.message


async def test_SE_146_data_testid_on_the_handle_should_be_relative(
    page: Page,
) -> None:
    await page.set_content(
        """
    <span data-testid="find-me" id=target1>1</span>
    <div>
      <span data-testid="find-me" id=target2>2</span>
    </div>
  """
    )
    assert await page.eval_on_selector("data-testid=find-me", "e => e.id") == "target1"

    div = await page.query_selector("div")
    assert div
    assert await div.eval_on_selector("data-testid=find-me", "e => e.id") == "target2"
    assert (
        await page.eval_on_selector("div >> data-testid=find-me", "e => e.id")
        == "target2"
    )


async def test_SE_147_should_properly_determine_visibility_of_display_contents_elements(
    page: Page,
) -> None:
    # https://github.com/microsoft/playwright/issues/11202
    await page.set_content(
        """
    <div>
      <p style="display:contents">DISPLAY CONTENTS</p>
    </div>"""
    )
    await page.wait_for_selector('"DISPLAY CONTENTS"')

    await page.set_content(
        """
    <div>
      <article style="display:contents"><div>DISPLAY CONTENTS</div></article>
    </div>"""
    )
    await page.wait_for_selector("article")

    await page.set_content(
        """
    <div>
      <article style="display:contents"><div style="display:contents">DISPLAY CONTENTS</div></article>
    </div>"""
    )
    await page.wait_for_selector("article")

    await page.set_content(
        """
    <div>
      <article style="display:contents"><div></div>DISPLAY CONTENTS<span></span></article>
    </div>"""
    )
    await page.wait_for_selector("article")

    await page.set_content(
        """
    <div>
      <article style="display:contents"><div></div></article>
    </div>"""
    )
    await page.wait_for_selector("article", state="hidden")


async def test_SE_148_should_work_with_internal_has(page: Page, server: Server) -> None:
    async def count(selector: str) -> int:
        return await page.eval_on_selector_all(selector, "els => els.length")

    async def outer_html(selector: str) -> str:
        return await page.eval_on_selector(selector, "e => e.outerHTML")

    await page.goto(server.PREFIX + "/deep-shadow.html")
    assert await count('div >> internal:has="#target"') == 2
    assert await count('div >> internal:has="[data-testid=foo]"') == 3
    assert await count('div >> internal:has="[attr*=value]"') == 2

    await page.set_content(
        "<section><span></span><div></div></section><section><br></section>"
    )
    assert await count('section >> internal:has="span, div"') == 1
    assert await count('section >> internal:has="span, div"') == 1
    assert await count('section >> internal:has="br"') == 1
    assert await count('section >> internal:has="span, br"') == 2
    assert await count('section >> internal:has="span, br, div"') == 2

    await page.set_content("<div><span>hello</span></div><div><span>world</span></div>")
    assert await count('div >> internal:has="text=world"') == 1
    assert (
        await outer_html('div >> internal:has="text=world"')
        == "<div><span>world</span></div>"
    )
    assert await count('div >> internal:has="text=\\"hello\\""') == 1
    assert (
        await outer_html('div >> internal:has="text=\\"hello\\""')
        == "<div><span>hello</span></div>"
    )
    assert await count('div >> internal:has="xpath=./span"') == 2
    assert await count('div >> internal:has="span"') == 2
    assert await count('div >> internal:has="span >> text=wor"') == 1
    assert (
        await outer_html('div >> internal:has="span >> text=wor"')
        == "<div><span>world</span></div>"
    )
    assert (
        await outer_html('div >> internal:has="span >> text=wor" >> span')
        == "<span>world</span>"
    )

    with pytest.raises(Error) as exc_info:
        await page.query_selector("div >> internal:has=abc")
    assert "Malformed selector: internal:has=abc" in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        await page.query_selector('internal:has="div"')
    assert '"internal:has" selector cannot be first' in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        await page.query_selector("div >> internal:has=33")
    assert "Malformed selector: internal:has=33" in exc_info.value.message
    with pytest.raises(Error) as exc_info:
        await page.query_selector('div >> internal:has="span!"')
    assert (
        'Unexpected token "!" while parsing css selector "span!"'
        in exc_info.value.message
    )


async def test_SE_149_should_work_with_internal_has_not(page: Page) -> None:
    async def count(selector: str) -> int:
        return await page.eval_on_selector_all(selector, "els => els.length")

    await page.set_content(
        "<section><span></span><div></div></section><section><br></section>"
    )
    assert await count('section >> internal:has-not="span"') == 1
    assert await count('section >> internal:has-not="span, div, br"') == 0
    assert await count('section >> internal:has-not="br"') == 1
    assert await count('section >> internal:has-not="span, div"') == 1
    assert await count('section >> internal:has-not="article"') == 2


async def test_SE_150_should_work_with_internal_and(page: Page, server: Server) -> None:
    async def texts(selector: str) -> List[str]:
        return await page.eval_on_selector_all(
            selector, "els => els.map(e => e.textContent)"
        )

    await page.set_content(
        """
    <div class=foo>hello</div><div class=bar>world</div>
    <span class=foo>hello2</span><span class=bar>world2</span>
  """
    )
    assert await texts('div >> internal:and="span"') == []
    assert await texts('div >> internal:and=".foo"') == ["hello"]
    assert await texts('div >> internal:and=".bar"') == ["world"]
    assert await texts('span >> internal:and="span"') == ["hello2", "world2"]
    assert await texts('.foo >> internal:and="div"') == ["hello"]
    assert await texts('.bar >> internal:and="span"') == ["world2"]


async def test_SE_151_should_work_with_internal_or(page: Page, server: Server) -> None:
    await page.set_content(
        """
    <div>hello</div>
    <span>world</span>
  """
    )
    assert await page.eval_on_selector_all(
        'div >> internal:or="span"', "els => els.map(e => e.textContent)"
    ) == ["hello", "world"]
    assert await page.eval_on_selector_all(
        'span >> internal:or="div"', "els => els.map(e => e.textContent)"
    ) == ["hello", "world"]
    assert (
        await page.eval_on_selector_all(
            'article >> internal:or="something"', "els => els.length"
        )
        == 0
    )
    assert await page.locator('article >> internal:or="div"').text_content() == "hello"
    assert await page.locator('article >> internal:or="span"').text_content() == "world"
    assert await page.locator('div >> internal:or="article"').text_content() == "hello"
    assert await page.locator('span >> internal:or="article"').text_content() == "world"


async def test_SE_152_should_work_with_internal_chain(
    page: Page, server: Server
) -> None:
    await page.set_content(
        """
    <div>one <span>two</span> <button>three</button> </div>
    <span>four</span>
    <button>five</button>
  """
    )
    assert await page.eval_on_selector_all(
        'div >> internal:chain="button"', "els => els.map(e => e.textContent)"
    ) == ["three"]
    assert await page.eval_on_selector_all(
        'div >> internal:chain="span >> internal:or=\\"button\\""',
        "els => els.map(e => e.textContent)",
    ) == ["two", "three"]


async def test_SE_153_chaining_should_work_with_large_dom_smoke(
    page: Page, server: Server
) -> None:
    await page.evaluate(
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
        counts.append(await page.eval_on_selector_all(selector, "els => els.length"))
    assert counts == [1, 1, 1]
