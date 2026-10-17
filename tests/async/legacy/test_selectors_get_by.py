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

from playwright.async_api import Page, expect


async def test_get_by_escaping(page: Page) -> None:
    await page.set_content(
        """
        <label id=label for=control>Hello my
wo"rld</label><input id=control />"""
    )
    await page.eval_on_selector(
        "input",
        """input => {
        input.setAttribute('placeholder', 'hello my\\nwo"rld');
        input.setAttribute('title', 'hello my\\nwo"rld');
        input.setAttribute('alt', 'hello my\\nwo"rld');
    }""",
    )
    await expect(page.get_by_text('hello my\nwo"rld')).to_have_attribute("id", "label")
    await expect(page.get_by_text('hello       my     wo"rld')).to_have_attribute(
        "id", "label"
    )
    await expect(page.get_by_label('hello my\nwo"rld')).to_have_attribute(
        "id", "control"
    )
    await expect(page.get_by_placeholder('hello my\nwo"rld')).to_have_attribute(
        "id", "control"
    )
    await expect(page.get_by_alt_text('hello my\nwo"rld')).to_have_attribute(
        "id", "control"
    )
    await expect(page.get_by_title('hello my\nwo"rld')).to_have_attribute(
        "id", "control"
    )

    await page.set_content(
        """
        <label id=label for=control>Hello my
world</label><input id=control />"""
    )
    await page.eval_on_selector(
        "input",
        """input => {
        input.setAttribute('placeholder', 'hello my\\nworld');
        input.setAttribute('title', 'hello my\\nworld');
        input.setAttribute('alt', 'hello my\\nworld');
    }""",
    )
    await expect(page.get_by_text("hello my\nworld")).to_have_attribute("id", "label")
    await expect(page.get_by_text("hello        my    world")).to_have_attribute(
        "id", "label"
    )
    await expect(page.get_by_label("hello my\nworld")).to_have_attribute(
        "id", "control"
    )
    await expect(page.get_by_placeholder("hello my\nworld")).to_have_attribute(
        "id", "control"
    )
    await expect(page.get_by_alt_text("hello my\nworld")).to_have_attribute(
        "id", "control"
    )
    await expect(page.get_by_title("hello my\nworld")).to_have_attribute(
        "id", "control"
    )

    await page.set_content("""<div id=target title="my title">Text here</div>""")
    await expect(page.get_by_title("my title", exact=True)).to_have_count(
        1, timeout=500
    )
    await expect(page.get_by_title("my t\\itle", exact=True)).to_have_count(
        0, timeout=500
    )
    await expect(page.get_by_title("my t\\\\itle", exact=True)).to_have_count(
        0, timeout=500
    )

    await page.set_content(
        """<label for=target>foo &gt;&gt; bar</label><input id=target>"""
    )
    await page.eval_on_selector(
        "input",
        """input => {
        input.setAttribute('placeholder', 'foo >> bar');
        input.setAttribute('title', 'foo >> bar');
        input.setAttribute('alt', 'foo >> bar');
    }""",
    )
    assert await page.get_by_text("foo >> bar").text_content() == "foo >> bar"
    await expect(page.locator("label")).to_have_text("foo >> bar")
    await expect(page.get_by_text("foo >> bar")).to_have_text("foo >> bar")
    assert (
        await page.get_by_text(re.compile("foo >> bar")).text_content() == "foo >> bar"
    )
    await expect(page.get_by_label("foo >> bar")).to_have_attribute("id", "target")
    await expect(page.get_by_label(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )
    await expect(page.get_by_placeholder("foo >> bar")).to_have_attribute(
        "id", "target"
    )
    await expect(page.get_by_alt_text("foo >> bar")).to_have_attribute("id", "target")
    await expect(page.get_by_title("foo >> bar")).to_have_attribute("id", "target")
    await expect(page.get_by_placeholder(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )
    await expect(page.get_by_alt_text(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )
    await expect(page.get_by_title(re.compile("foo >> bar"))).to_have_attribute(
        "id", "target"
    )


async def test_get_by_role_escaping(
    page: Page,
) -> None:
    await page.set_content(
        """
        <a href="https://playwright.dev">issues 123</a>
        <a href="https://playwright.dev">he llo 56</a>
        <button>Click me</button>
    """
    )
    assert await page.get_by_role("button").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        "<button>Click me</button>",
    ]
    assert await page.get_by_role("link").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">issues 123</a>""",
        """<a href="https://playwright.dev">he llo 56</a>""",
    ]

    assert await page.get_by_role("link", name="issues 123").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">issues 123</a>""",
    ]
    assert await page.get_by_role("link", name="sues").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">issues 123</a>""",
    ]
    assert await page.get_by_role("link", name="  he    \n  llo ").evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        """<a href="https://playwright.dev">he llo 56</a>""",
    ]
    assert (
        await page.get_by_role("button", name="issues").evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )

    assert (
        await page.get_by_role("link", name="sues", exact=True).evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )
    assert await page.get_by_role(
        "link", name="   he \n llo 56 ", exact=True
    ).evaluate_all("els => els.map(e => e.outerHTML)") == [
        """<a href="https://playwright.dev">he llo 56</a>""",
    ]

    assert await page.get_by_role("button", name="Click me", exact=True).evaluate_all(
        "els => els.map(e => e.outerHTML)"
    ) == [
        "<button>Click me</button>",
    ]
    assert (
        await page.get_by_role("button", name="Click \\me", exact=True).evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )
    assert (
        await page.get_by_role("button", name="Click \\\\me", exact=True).evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )


async def test_include_hidden_should_work(
    page: Page,
) -> None:
    await page.set_content("""<button style="display: none">Hidden</button>""")
    assert (
        await page.get_by_role("button", name="Hidden").evaluate_all(
            "els => els.map(e => e.outerHTML)"
        )
        == []
    )
    assert await page.get_by_role(
        "button", name="Hidden", include_hidden=True
    ).evaluate_all("els => els.map(e => e.outerHTML)") == [
        """<button style="display: none">Hidden</button>""",
    ]
