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

"""Port of tests/page/selectors-text.spec.ts."""

import asyncio
import re

import pytest

from playwright.async_api import Error, Page, expect
from tests.server import Server

OUTER = "e => e.outerHTML"
ID = "e => e.id"
COUNT = "els => els.length"


async def test_SE_028_should_work_smoke(page: Page) -> None:
    await page.set_content("<div>yo</div><div>ya</div><div>\nye  </div>")
    assert await page.eval_on_selector("text=ya", OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector('text="ya"', OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("text=/^[ay]+$/", OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("text=/Ya/i", OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("text=ye", OUTER) == "<div>\nye  </div>"
    assert ">\nye  </div>" in await page.get_by_text("ye").evaluate(OUTER)

    await page.set_content("<div> ye </div><div>ye</div>")
    assert await page.eval_on_selector('text="ye"', OUTER) == "<div> ye </div>"
    assert "> ye </div>" in await page.get_by_text("ye", exact=True).first.evaluate(
        OUTER
    )

    await page.set_content('<div>yo</div><div>"ya</div><div> hello world! </div>')
    assert await page.eval_on_selector('text="\\"ya"', OUTER) == '<div>"ya</div>'
    assert (
        await page.eval_on_selector("text=/hello/", OUTER)
        == "<div> hello world! </div>"
    )
    assert (
        await page.eval_on_selector(r"text=/^\s*heLLo/i", OUTER)
        == "<div> hello world! </div>"
    )

    await page.set_content("<div>yo<div>ya</div>hey<div>hey</div></div>")
    assert await page.eval_on_selector("text=hey", OUTER) == "<div>hey</div>"
    assert await page.eval_on_selector('text=yo>>text="ya"', OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector('text=yo>> text="ya"', OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("text=yo >>text='ya'", OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("text=yo >> text='ya'", OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("'yo'>>\"ya\"", OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector("\"yo\" >> 'ya'", OUTER) == "<div>ya</div>"

    await page.set_content(
        '<div>yo<span id="s1"></span></div><div>yo<span id="s2"></span><span id="s3"></span></div>'
    )
    assert (
        await page.eval_on_selector_all(
            "text=yo", "es => es.map(e => e.outerHTML).join('\\n')"
        )
        == '<div>yo<span id="s1"></span></div>\n<div>yo<span id="s2"></span><span id="s3"></span></div>'
    )

    await page.set_content("<div>'</div><div>\"</div><div>\\</div><div>x</div>")
    assert await page.eval_on_selector("text='\\''", OUTER) == "<div>'</div>"
    assert await page.eval_on_selector("text='\"'", OUTER) == '<div>"</div>'
    assert await page.eval_on_selector('text="\\""', OUTER) == '<div>"</div>'
    assert await page.eval_on_selector('text="\'"', OUTER) == "<div>'</div>"
    assert await page.eval_on_selector('text="\\x"', OUTER) == "<div>x</div>"
    assert await page.eval_on_selector("text='\\x'", OUTER) == "<div>x</div>"
    assert await page.eval_on_selector("text='\\\\'", OUTER) == "<div>\\</div>"
    assert await page.eval_on_selector('text="\\\\"', OUTER) == "<div>\\</div>"
    assert await page.eval_on_selector('text="', OUTER) == '<div>"</div>'
    assert await page.eval_on_selector("text='", OUTER) == "<div>'</div>"
    assert await page.eval_on_selector('"x"', OUTER) == "<div>x</div>"
    assert await page.eval_on_selector("'x'", OUTER) == "<div>x</div>"
    with pytest.raises(Error):
        await page.query_selector('"')
    with pytest.raises(Error):
        await page.query_selector("'")

    await page.set_content("<div> ' </div><div> \" </div>")
    assert await page.eval_on_selector('text="', OUTER) == '<div> " </div>'
    assert await page.eval_on_selector("text='", OUTER) == "<div> ' </div>"

    await page.set_content("<div>Hi''&gt;&gt;foo=bar</div>")
    assert (
        await page.eval_on_selector("text=\"Hi''>>foo=bar\"", OUTER)
        == "<div>Hi''&gt;&gt;foo=bar</div>"
    )
    await page.set_content("<div>Hi'\"&gt;&gt;foo=bar</div>")
    assert (
        await page.eval_on_selector('text="Hi\'\\">>foo=bar"', OUTER)
        == "<div>Hi'\"&gt;&gt;foo=bar</div>"
    )

    await page.set_content("<div>Hi&gt;&gt;<span></span></div>")
    assert await page.eval_on_selector('text="Hi>>">>span', OUTER) == "<span></span>"
    assert (
        await page.eval_on_selector(r"text=/Hi\>\>/ >> span", OUTER) == "<span></span>"
    )

    await page.set_content("<div>a<br>b</div><div>a</div>")
    assert await page.eval_on_selector("text=a", OUTER) == "<div>a<br>b</div>"
    assert await page.eval_on_selector("text=b", OUTER) == "<div>a<br>b</div>"
    assert await page.eval_on_selector("text=ab", OUTER) == "<div>a<br>b</div>"
    assert await page.query_selector("text=abc") is None
    assert await page.eval_on_selector_all("text=a", COUNT) == 2
    assert await page.eval_on_selector_all("text=b", COUNT) == 1
    assert await page.eval_on_selector_all("text=ab", COUNT) == 1
    assert await page.eval_on_selector_all("text=abc", COUNT) == 0

    await page.set_content("<div></div><span></span>")
    await page.eval_on_selector(
        "div",
        """div => {
        div.appendChild(document.createTextNode('hello'));
        div.appendChild(document.createTextNode('world'));
      }""",
    )
    await page.eval_on_selector(
        "span",
        """span => {
        span.appendChild(document.createTextNode('hello'));
        span.appendChild(document.createTextNode('world'));
      }""",
    )
    assert await page.eval_on_selector("text=lowo", OUTER) == "<div>helloworld</div>"
    assert (
        await page.eval_on_selector_all(
            "text=lowo", "els => els.map(e => e.outerHTML).join('')"
        )
        == "<div>helloworld</div><span>helloworld</span>"
    )

    await page.set_content("<span>Sign&nbsp;in</span><span>Hello\n \nworld</span>")
    assert (
        await page.eval_on_selector("text=Sign in", OUTER)
        == "<span>Sign&nbsp;in</span>"
    )
    assert len(await page.query_selector_all("text=Sign \tin")) == 1
    assert len(await page.query_selector_all('text="Sign in"')) == 1
    assert (
        await page.eval_on_selector("text=lo wo", OUTER)
        == "<span>Hello\n \nworld</span>"
    )
    assert (
        await page.eval_on_selector('text="Hello world"', OUTER)
        == "<span>Hello\n \nworld</span>"
    )
    assert await page.query_selector('text="lo wo"') is None
    assert len(await page.query_selector_all("text=lo \nwo")) == 1
    assert len(await page.query_selector_all('text="lo \nwo"')) == 0

    await page.set_content("<div>let's<span>hello</span></div>")
    assert (
        await page.eval_on_selector("text=/let's/i >> span", OUTER)
        == "<span>hello</span>"
    )
    assert (
        await page.eval_on_selector(r"text=/let\'s/i >> span", OUTER)
        == "<span>hello</span>"
    )


async def test_SE_029_should_work_with_text(page: Page) -> None:
    await page.set_content("<div>yo</div><div>ya</div><div>\nHELLO   \n world  </div>")
    assert await page.eval_on_selector(':text("ya")', OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector(':text-is("ya")', OUTER) == "<div>ya</div>"
    assert await page.eval_on_selector(':text("y")', OUTER) == "<div>yo</div>"
    assert await page.query_selector(':text-is("Y")') is None
    assert (
        await page.eval_on_selector(':text("hello world")', OUTER)
        == "<div>\nHELLO   \n world  </div>"
    )
    assert (
        await page.eval_on_selector(':text-is("HELLO world")', OUTER)
        == "<div>\nHELLO   \n world  </div>"
    )
    assert (
        await page.eval_on_selector(':text("lo wo")', OUTER)
        == "<div>\nHELLO   \n world  </div>"
    )
    assert await page.query_selector(':text-is("lo wo")') is None
    assert (
        await page.eval_on_selector(':text-matches("^[ay]+$")', OUTER)
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector(':text-matches("y", "g")', OUTER) == "<div>yo</div>"
    )
    assert (
        await page.eval_on_selector(':text-matches("Y", "i")', OUTER) == "<div>yo</div>"
    )
    assert await page.query_selector(':text-matches("^y$")') is None

    with pytest.raises(Error) as exc_info1:
        await page.query_selector(':text("foo", "bar")')
    assert '"text" engine expects a single string' in exc_info1.value.message
    with pytest.raises(Error) as exc_info2:
        await page.query_selector(":text(foo > bar)")
    assert '"text" engine expects a single string' in exc_info2.value.message


async def test_SE_030_should_support_empty_string(page: Page) -> None:
    await page.set_content("<div></div><div>ya</div><div>\nHELLO   \n world  </div>")
    assert await page.eval_on_selector('div:text-is("")', OUTER) == "<div></div>"
    assert await page.eval_on_selector_all('div:text-is("")', COUNT) == 1
    assert await page.eval_on_selector('div:text("")', OUTER) == "<div></div>"
    assert await page.eval_on_selector_all('div:text("")', COUNT) == 3
    assert await page.eval_on_selector('div >> text=""', OUTER) == "<div></div>"
    assert await page.eval_on_selector_all('div >> text=""', COUNT) == 1
    assert await page.eval_on_selector("div >> text=/^$/", OUTER) == "<div></div>"
    assert await page.eval_on_selector_all("div >> text=/^$/", COUNT) == 1
    assert await page.eval_on_selector('div:text-matches("")', OUTER) == "<div></div>"
    assert await page.eval_on_selector_all('div:text-matches("")', COUNT) == 3


async def test_SE_031_should_work_across_nodes(page: Page) -> None:
    await page.set_content(
        "<div id=target1>Hello<i>,</i> <span id=target2>world</span><b>!</b></div>"
    )

    assert await page.eval_on_selector(':text("Hello, world!")', ID) == "target1"
    assert await page.eval_on_selector(':text("Hello")', ID) == "target1"
    assert await page.eval_on_selector(':text("world")', ID) == "target2"
    assert await page.eval_on_selector_all(':text("world")', COUNT) == 1
    assert await page.query_selector(':text("hello world")') is None
    assert await page.query_selector('div:text("world")') is None
    assert await page.eval_on_selector("text=Hello, world!", ID) == "target1"
    assert await page.eval_on_selector("text=Hello", ID) == "target1"
    assert await page.eval_on_selector("text=world", ID) == "target2"
    assert await page.eval_on_selector_all("text=world", COUNT) == 1
    assert await page.query_selector("text=hello world") is None

    assert await page.query_selector(':text-is("Hello, world!")') is None
    assert await page.eval_on_selector(':text-is("Hello")', ID) == "target1"
    assert await page.eval_on_selector(':text-is("world")', ID) == "target2"
    assert await page.eval_on_selector_all(':text-is("world")', COUNT) == 1
    assert await page.query_selector('text="Hello, world!"') is None
    assert await page.eval_on_selector('text="Hello"', ID) == "target1"
    assert await page.eval_on_selector('text="world"', ID) == "target2"
    assert await page.eval_on_selector_all('text="world"', COUNT) == 1

    assert await page.eval_on_selector(':text-matches(".*")', "e => e.nodeName") == "I"
    assert await page.eval_on_selector(':text-matches("world?")', ID) == "target2"
    assert await page.eval_on_selector_all(':text-matches("world")', COUNT) == 1
    assert await page.query_selector('div:text(".*")') is None
    assert await page.eval_on_selector("text=/.*/", "e => e.nodeName") == "I"
    assert await page.eval_on_selector("text=/world?/", ID) == "target2"
    assert await page.eval_on_selector_all("text=/world/", COUNT) == 1


async def test_SE_032_text_is_should_ignore_comments(page: Page) -> None:
    await page.set_content(
        """<div id=me>hel<!-- comment -->lo
  <!-- comment -->
  world</div>"""
    )
    assert await page.eval_on_selector(':text-is("hello world")', ID) == "me"
    assert await page.locator("div", has_text="hello world").get_attribute("id") == "me"
    assert await page.get_by_text("hello world", exact=True).get_attribute("id") == "me"


async def test_SE_033_should_work_with_text_nodes_in_quoted_mode(page: Page) -> None:
    await page.set_content(
        "<div id=target1>Hello<span id=target2>wo  rld  </span>  Hi again  </div>"
    )
    assert await page.eval_on_selector('text="Hello"', ID) == "target1"
    assert await page.eval_on_selector('text="Hi again"', ID) == "target1"
    assert await page.eval_on_selector('text="wo rld"', ID) == "target2"
    assert await page.query_selector('text="Hellowo rld Hi again"') is None
    assert await page.query_selector('text="Hellowo"') is None
    assert await page.query_selector('text="Hellowo rld"') is None
    assert await page.query_selector('text="wo rld Hi ag"') is None
    assert await page.query_selector('text="again"') is None
    assert await page.query_selector('text="hi again"') is None
    assert await page.eval_on_selector("text=hi again", ID) == "target1"


async def test_SE_034_should_clear_caches(page: Page) -> None:
    await page.set_content("<div id=target1>text</div><div id=target2>text</div>")
    div = await page.query_selector("#target1")
    assert div

    await div.evaluate("div => div.textContent = 'text'")
    assert await page.eval_on_selector("text=text", ID) == "target1"
    await div.evaluate("div => div.textContent = 'foo'")
    assert await page.eval_on_selector("text=text", ID) == "target2"

    await div.evaluate("div => div.textContent = 'text'")
    assert await page.eval_on_selector(':text("text")', ID) == "target1"
    await div.evaluate("div => div.textContent = 'foo'")
    assert await page.eval_on_selector(':text("text")', ID) == "target2"

    await div.evaluate("div => div.textContent = 'text'")
    assert await page.eval_on_selector_all("text=text", COUNT) == 2
    await div.evaluate("div => div.textContent = 'foo'")
    assert await page.eval_on_selector_all("text=text", COUNT) == 1

    await div.evaluate("div => div.textContent = 'text'")
    assert await page.eval_on_selector_all(':text("text")', COUNT) == 2
    await div.evaluate("div => div.textContent = 'foo'")
    assert await page.eval_on_selector_all(':text("text")', COUNT) == 1


async def test_SE_035_should_work_with_has_text(page: Page) -> None:
    await page.set_content(
        """
    <input id=input2>
    <div id=div1>
      <span>  Find me  </span>
      or
      <wrap><span id=span2>maybe me  </span></wrap>
      <div><input id=input1></div>
    </div>
  """
    )
    assert await page.eval_on_selector(':has-text("find me")', "e => e.tagName") == (
        "HTML"
    )
    assert (
        await page.eval_on_selector('span:has-text("find me")', OUTER)
        == "<span>  Find me  </span>"
    )
    assert await page.eval_on_selector('div:has-text("find me")', ID) == "div1"
    assert await page.eval_on_selector('div:has-text("find me") input', ID) == "input1"
    assert await page.eval_on_selector(':has-text("find me") input', ID) == "input2"
    assert (
        await page.eval_on_selector('div:has-text("find me or maybe me")', ID) == "div1"
    )
    assert await page.query_selector('div:has-text("find noone")') is None
    assert (
        await page.eval_on_selector_all(
            ':is(div,span):has-text("maybe")', "els => els.map(e => e.id).join(';')"
        )
        == "div1;span2"
    )
    assert (
        await page.eval_on_selector(
            'div:has-text("find me") :has-text("maybe me")', "e => e.tagName"
        )
        == "WRAP"
    )
    assert (
        await page.eval_on_selector(
            'div:has-text("find me") span:has-text("maybe me")', ID
        )
        == "span2"
    )

    await page.set_content(
        """<div id=me>hello
  wo"r>>ld</div>"""
    )
    assert await page.eval_on_selector(r'div:has-text("hello wo\"r>>ld")', ID) == "me"
    assert await page.eval_on_selector(r'div:has-text("hello\a wo\"r>>ld")', ID) == "me"
    assert (
        await page.locator("div", has_text='hello\nwo"r>>ld').get_attribute("id")
        == "me"
    )

    with pytest.raises(Error) as exc_info1:
        await page.query_selector(':has-text("foo", "bar")')
    assert '"has-text" engine expects a single string' in exc_info1.value.message
    with pytest.raises(Error) as exc_info2:
        await page.query_selector(":has-text(foo > bar)")
    assert '"has-text" engine expects a single string' in exc_info2.value.message


async def test_SE_036_should_work_with_large_dom(page: Page) -> None:
    await page.evaluate(
        """() => {
        let id = 0;
        const next = (tag) => {
          const e = document.createElement(tag);
          const eid = ++id;
          e.textContent = 'id' + eid;
          e.id = 'id' + eid;
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
        ':has-text("id18")',
        ':has-text("id12345")',
        ':has-text("id")',
        ':text("id18")',
        ':text("id12345")',
        ':text("id")',
        ':text-matches("id12345", "i")',
        "text=id18",
        "text=id12345",
        "text=id",
        "#id18",
        "#id12345",
        "*",
    ]

    for selector in selectors:
        await page.eval_on_selector_all(selector, COUNT)


async def test_SE_037_should_be_case_sensitive_if_quotes_are_specified(
    page: Page,
) -> None:
    await page.set_content("<div>yo</div><div>ya</div><div>\nye  </div>")
    assert await page.eval_on_selector("text=yA", OUTER) == "<div>ya</div>"
    assert await page.query_selector('text="yA"') is None
    assert await page.query_selector('text= "ya"') is None


async def test_SE_038_should_search_for_a_substring_without_quotes(
    page: Page,
) -> None:
    await page.set_content("<div>textwithsubstring</div>")
    assert (
        await page.eval_on_selector("text=with", OUTER)
        == "<div>textwithsubstring</div>"
    )
    assert await page.query_selector('text="with"') is None


async def test_SE_039_should_skip_head_script_and_style(page: Page) -> None:
    await page.set_content(
        """
    <head>
      <title>title</title>
      <script>var script</script>
      <style>.style {}</style>
    </head>
    <body>
      <script>var script</script>
      <style>.style {}</style>
      <div>title script style</div>
    </body>"""
    )
    head = await page.query_selector("head")
    title = await page.query_selector("title")
    script = await page.query_selector("body script")
    style = await page.query_selector("body style")
    for text in ["title", "script", "style"]:
        assert await page.eval_on_selector(f"text={text}", "e => e.nodeName") == "DIV"
        assert (
            await page.eval_on_selector_all(
                f"text={text}", "els => els.map(e => e.nodeName).join('|')"
            )
            == "DIV"
        )
        for root in [head, title, script, style]:
            assert root
            assert await root.query_selector(f"text={text}") is None
            assert await root.eval_on_selector_all(f"text={text}", COUNT) == 0


async def test_SE_040_should_match_input_type_button_submit_reset(
    page: Page,
) -> None:
    await page.set_content(
        '<input type="submit" value="hello"><input type="button" value="world"><input type="reset" value="clear">'
    )
    assert (
        await page.eval_on_selector("text=hello", OUTER)
        == '<input type="submit" value="hello">'
    )
    assert (
        await page.eval_on_selector("text=world", OUTER)
        == '<input type="button" value="world">'
    )
    assert (
        await page.eval_on_selector("text=clear", OUTER)
        == '<input type="reset" value="clear">'
    )


async def test_SE_041_should_work_for_open_shadow_roots(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/deep-shadow.html")
    text = "e => e.textContent"
    assert await page.eval_on_selector("text=root1", text) == "Hello from root1"
    assert await page.eval_on_selector("text=root2", text) == "Hello from root2"
    assert await page.eval_on_selector("text=root3", text) == "Hello from root3"
    assert (
        await page.eval_on_selector("#root1 >> text=from root3", text)
        == "Hello from root3"
    )
    assert (
        await page.eval_on_selector("#target >> text=from root2", text)
        == "Hello from root2"
    )
    assert await page.query_selector("text:light=root1") is None
    assert await page.query_selector("text:light=root2") is None
    assert await page.query_selector("text:light=root3") is None


async def test_SE_042_should_prioritize_light_dom_over_shadow_dom_in_the_same_parent(
    page: Page,
) -> None:
    await page.evaluate(
        """() => {
        const div = document.createElement('div');
        document.body.appendChild(div);

        div.attachShadow({ mode: 'open' });
        const shadowSpan = document.createElement('span');
        shadowSpan.textContent = 'Hello from shadow';
        div.shadowRoot.appendChild(shadowSpan);

        const lightSpan = document.createElement('span');
        lightSpan.textContent = 'Hello from light';
        div.appendChild(lightSpan);
      }"""
    )
    assert (
        await page.eval_on_selector("div >> text=Hello", "e => e.textContent")
        == "Hello from light"
    )


async def test_SE_043_should_wait_for_selector_with_distributed_elements(
    page: Page,
) -> None:
    task = asyncio.create_task(page.wait_for_selector("div >> text=Hello"))
    await page.evaluate(
        """() => {
        const div = document.createElement('div');
        document.body.appendChild(div);

        div.attachShadow({ mode: 'open' });
        const shadowSpan = document.createElement('span');
        shadowSpan.textContent = 'Hello from shadow';
        div.shadowRoot.appendChild(shadowSpan);
        div.shadowRoot.appendChild(document.createElement('slot'));

        const lightSpan = document.createElement('span');
        lightSpan.textContent = 'Hello from light';
        div.appendChild(lightSpan);
      }"""
    )
    handle = await task
    assert handle
    assert await handle.text_content() == "Hello from light"


async def test_SE_044_should_match_root_after(page: Page) -> None:
    await page.set_content("<section>test</section>")
    element = await page.query_selector("css=section >> text=test")
    assert element
    element2 = await page.query_selector("text=test >> text=test")
    assert element2


async def test_SE_045_should_match_root_after_with(page: Page) -> None:
    await page.set_content(
        "<button> hello world </button> <button> hellow <span> world </span> </button>"
    )
    assert (
        await page.eval_on_selector_all(
            "*css=button >> text=hello >> text=world", COUNT
        )
        == 2
    )


async def test_SE_046_should_work_with_leading_and_trailing_spaces(
    page: Page,
) -> None:
    await page.set_content("<button> Add widget </button>")
    await expect(page.locator("text=Add widget")).to_be_visible()
    await expect(page.locator("text= Add widget ")).to_be_visible()


async def test_SE_047_should_work_with_unpaired_quotes_when_not_at_the_start(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div>hello"world<span>yay</span></div>
    <div>hello'world<span>nay</span></div>
    <div>hello`world<span>oh</span></div>
    <div>hello`world<span>oh2</span></div>
  """
    )
    assert await page.eval_on_selector('text=lo" >> span', OUTER) == "<span>yay</span>"
    assert (
        await page.eval_on_selector('  text=lo" >> span', OUTER) == "<span>yay</span>"
    )
    assert (
        await page.eval_on_selector('text  =lo" >> span', OUTER) == "<span>yay</span>"
    )
    assert (
        await page.eval_on_selector('text=  lo" >> span', OUTER) == "<span>yay</span>"
    )
    assert (
        await page.eval_on_selector(' text = lo" >> span', OUTER) == "<span>yay</span>"
    )
    assert (
        await page.eval_on_selector('text=o"wor >> span', OUTER) == "<span>yay</span>"
    )

    assert (
        await page.eval_on_selector("text=lo'wor >> span", OUTER) == "<span>nay</span>"
    )
    assert await page.eval_on_selector("text=o' >> span", OUTER) == "<span>nay</span>"

    assert (
        await page.eval_on_selector("text=ello`wor >> span", OUTER) == "<span>oh</span>"
    )
    await expect(page.locator("text=ello`wor").locator("span").first).to_have_text("oh")
    await expect(page.locator("text=ello`wor").locator("span").nth(1)).to_have_text(
        "oh2"
    )

    assert await page.query_selector("text='wor >> span") is None
    assert await page.query_selector('text=" >> span') is None
    assert await page.query_selector("text=` >> span") is None


async def test_SE_048_should_work_with_paired_quotes_in_the_middle_of_selector(
    page: Page,
) -> None:
    await page.set_content(r'<div>pattern "^-?\d+$"</div>')
    assert await page.locator(r'div >> text=pattern "^-?\d+$').is_visible()
    assert await page.locator(r'div >> text=pattern "^-?\d+$"').is_visible()
    # Should double escape inside quoted text.
    assert await page.locator(r"""div >> text='pattern "^-?\\d+$"'""").is_visible()
    await expect(page.locator(r'div >> text=pattern "^-?\d+$')).to_be_visible()
    await expect(page.locator(r'div >> text=pattern "^-?\d+$"')).to_be_visible()
    # Should double escape inside quoted text.
    await expect(page.locator(r"""div >> text='pattern "^-?\\d+$"'""")).to_be_visible()


async def test_SE_049_has_text_and_internal_text_should_match_full_node_text_in_strict_mode(
    page: Page,
) -> None:
    await page.set_content(
        """
    <div id=div1>hello<span>world</span></div>
    <div id=div2>hello</div>
  """
    )
    await expect(page.get_by_text("helloworld", exact=True)).to_have_id("div1")
    await expect(page.get_by_text("hello", exact=True)).to_have_id("div2")
    await expect(page.locator("div", has_text=re.compile(r"^helloworld$"))).to_have_id(
        "div1"
    )
    await expect(page.locator("div", has_text=re.compile(r"^hello$"))).to_have_id(
        "div2"
    )

    await page.set_content(
        """
    <div id=div1><span id=span1>hello</span>world</div>
    <div id=div2><span id=span2>hello</span></div>
  """
    )
    await expect(page.get_by_text("helloworld", exact=True)).to_have_id("div1")
    assert await page.get_by_text("hello", exact=True).evaluate_all(
        "els => els.map(e => e.id)"
    ) == ["span1", "span2"]
    await expect(page.locator("div", has_text=re.compile(r"^helloworld$"))).to_have_id(
        "div1"
    )
    await expect(page.locator("div", has_text=re.compile(r"^hello$"))).to_have_id(
        "div2"
    )
