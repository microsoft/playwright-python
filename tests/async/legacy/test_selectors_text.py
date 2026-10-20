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
import re

import pytest

from playwright.async_api import Error, Page, expect


async def test_has_text_and_internal_text_should_match_full_node_text_in_strict_mode(
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
    await expect(page.locator("div", has_text=re.compile("^helloworld$"))).to_have_id(
        "div1"
    )
    await expect(page.locator("div", has_text=re.compile("^hello$"))).to_have_id("div2")

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
    await expect(page.locator("div", has_text=re.compile("^helloworld$"))).to_have_id(
        "div1"
    )
    await expect(page.locator("div", has_text=re.compile("^hello$"))).to_have_id("div2")


async def test_should_work(page: Page) -> None:
    await page.set_content(
        """
        <div>yo</div><div>ya</div><div>\nye  </div>
    """
    )
    assert await page.eval_on_selector("text=ya", "e => e.outerHTML") == "<div>ya</div>"
    assert (
        await page.eval_on_selector('text="ya"', "e => e.outerHTML") == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("text=/^[ay]+$/", "e => e.outerHTML")
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("text=/Ya/i", "e => e.outerHTML") == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("text=ye", "e => e.outerHTML")
        == "<div>\nye  </div>"
    )
    assert ">\nye  </div>" in await page.get_by_text("ye").evaluate("e => e.outerHTML")

    await page.set_content(
        """
        <div> ye </div><div>ye</div>
    """
    )
    assert (
        await page.eval_on_selector('text="ye"', "e => e.outerHTML")
        == "<div> ye </div>"
    )
    assert "> ye </div>" in await page.get_by_text("ye", exact=True).first.evaluate(
        "e => e.outerHTML"
    )

    await page.set_content(
        """
        <div>yo</div><div>"ya</div><div> hello world! </div>
    """
    )
    assert (
        await page.eval_on_selector('text="\\"ya"', "e => e.outerHTML")
        == '<div>"ya</div>'
    )
    assert (
        await page.eval_on_selector("text=/hello/", "e => e.outerHTML")
        == "<div> hello world! </div>"
    )
    assert (
        await page.eval_on_selector("text=/^\\s*heLLo/i", "e => e.outerHTML")
        == "<div> hello world! </div>"
    )

    await page.set_content(
        """
        <div>yo<div>ya</div>hey<div>hey</div></div>
    """
    )
    assert (
        await page.eval_on_selector("text=hey", "e => e.outerHTML") == "<div>hey</div>"
    )
    assert (
        await page.eval_on_selector('text=yo>>text="ya"', "e => e.outerHTML")
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector('text=yo>> text="ya"', "e => e.outerHTML")
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("text=yo >>text='ya'", "e => e.outerHTML")
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("text=yo >> text='ya'", "e => e.outerHTML")
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("'yo'>>\"ya\"", "e => e.outerHTML")
        == "<div>ya</div>"
    )
    assert (
        await page.eval_on_selector("\"yo\" >> 'ya'", "e => e.outerHTML")
        == "<div>ya</div>"
    )

    await page.set_content(
        """
        <div>yo<span id="s1"></span></div><div>yo<span id="s2"></span><span id="s3"></span></div>
        """
    )
    assert (
        await page.eval_on_selector_all(
            "text=yo", "es => es.map(e => e.outerHTML).join('\\n')"
        )
        == '<div>yo<span id="s1"></span></div>\n<div>yo<span id="s2"></span><span id="s3"></span></div>'
    )

    await page.set_content("<div>'</div><div>\"</div><div>\\</div><div>x</div>")
    assert (
        await page.eval_on_selector("text='\\''", "e => e.outerHTML") == "<div>'</div>"
    )
    assert (
        await page.eval_on_selector("text='\"'", "e => e.outerHTML") == '<div>"</div>'
    )
    assert (
        await page.eval_on_selector('text="\\""', "e => e.outerHTML") == '<div>"</div>'
    )
    assert (
        await page.eval_on_selector('text="\'"', "e => e.outerHTML") == "<div>'</div>"
    )
    assert (
        await page.eval_on_selector('text="\\x"', "e => e.outerHTML") == "<div>x</div>"
    )
    assert (
        await page.eval_on_selector("text='\\x'", "e => e.outerHTML") == "<div>x</div>"
    )
    assert (
        await page.eval_on_selector("text='\\\\'", "e => e.outerHTML")
        == "<div>\\</div>"
    )
    assert (
        await page.eval_on_selector('text="\\\\"', "e => e.outerHTML")
        == "<div>\\</div>"
    )
    assert await page.eval_on_selector('text="', "e => e.outerHTML") == '<div>"</div>'
    assert await page.eval_on_selector("text='", "e => e.outerHTML") == "<div>'</div>"
    assert await page.eval_on_selector('"x"', "e => e.outerHTML") == "<div>x</div>"
    assert await page.eval_on_selector("'x'", "e => e.outerHTML") == "<div>x</div>"
    with pytest.raises(Error):
        await page.query_selector_all('"')
    with pytest.raises(Error):
        await page.query_selector_all("'")

    await page.set_content("<div> ' </div><div> \" </div>")
    assert await page.eval_on_selector('text="', "e => e.outerHTML") == '<div> " </div>'
    assert await page.eval_on_selector("text='", "e => e.outerHTML") == "<div> ' </div>"

    await page.set_content("<div>Hi''&gt;&gt;foo=bar</div>")
    assert (
        await page.eval_on_selector("text=\"Hi''>>foo=bar\"", "e => e.outerHTML")
        == "<div>Hi''&gt;&gt;foo=bar</div>"
    )
    await page.set_content("<div>Hi'\"&gt;&gt;foo=bar</div>")
    assert (
        await page.eval_on_selector('text="Hi\'\\">>foo=bar"', "e => e.outerHTML")
        == "<div>Hi'\"&gt;&gt;foo=bar</div>"
    )

    await page.set_content("<div>Hi&gt;&gt;<span></span></div>")
    assert (
        await page.eval_on_selector('text="Hi>>">>span', "e => e.outerHTML")
        == "<span></span>"
    )
    assert (
        await page.eval_on_selector("text=/Hi\\>\\>/ >> span", "e => e.outerHTML")
        == "<span></span>"
    )

    await page.set_content("<div>a<br>b</div><div>a</div>")
    assert (
        await page.eval_on_selector("text=a", "e => e.outerHTML") == "<div>a<br>b</div>"
    )
    assert (
        await page.eval_on_selector("text=b", "e => e.outerHTML") == "<div>a<br>b</div>"
    )
    assert (
        await page.eval_on_selector("text=ab", "e => e.outerHTML")
        == "<div>a<br>b</div>"
    )
    assert await page.query_selector("text=abc") is None
    assert await page.eval_on_selector_all("text=a", "els => els.length") == 2
    assert await page.eval_on_selector_all("text=b", "els => els.length") == 1
    assert await page.eval_on_selector_all("text=ab", "els => els.length") == 1
    assert await page.eval_on_selector_all("text=abc", "els => els.length") == 0

    await page.set_content("<div></div><span></span>")
    await page.eval_on_selector(
        "div",
        """div => {
        div.appendChild(document.createTextNode('hello'))
        div.appendChild(document.createTextNode('world'))
    }""",
    )
    await page.eval_on_selector(
        "span",
        """span => {
        span.appendChild(document.createTextNode('hello'))
        span.appendChild(document.createTextNode('world'))
    }""",
    )
    assert (
        await page.eval_on_selector("text=lowo", "e => e.outerHTML")
        == "<div>helloworld</div>"
    )
    assert (
        await page.eval_on_selector_all(
            "text=lowo", "els => els.map(e => e.outerHTML).join('')"
        )
        == "<div>helloworld</div><span>helloworld</span>"
    )

    await page.set_content("<span>Sign&nbsp;in</span><span>Hello\n \nworld</span>")
    assert (
        await page.eval_on_selector("text=Sign in", "e => e.outerHTML")
        == "<span>Sign&nbsp;in</span>"
    )
    assert len((await page.query_selector_all("text=Sign \tin"))) == 1
    assert len((await page.query_selector_all('text="Sign in"'))) == 1
    assert (
        await page.eval_on_selector("text=lo wo", "e => e.outerHTML")
        == "<span>Hello\n \nworld</span>"
    )
    assert (
        await page.eval_on_selector('text="Hello world"', "e => e.outerHTML")
        == "<span>Hello\n \nworld</span>"
    )
    assert await page.query_selector('text="lo wo"') is None
    assert len((await page.query_selector_all("text=lo \nwo"))) == 1
    assert len(await page.query_selector_all('text="lo \nwo"')) == 0

    await page.set_content("<div>let's<span>hello</span></div>")
    assert (
        await page.eval_on_selector("text=/let's/i >> span", "e => e.outerHTML")
        == "<span>hello</span>"
    )
    assert (
        await page.eval_on_selector("text=/let\\'s/i >> span", "e => e.outerHTML")
        == "<span>hello</span>"
    )
