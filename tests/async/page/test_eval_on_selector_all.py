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

"""Port of tests/page/eval-on-selector-all.spec.ts."""

from playwright.async_api import Page


async def test_ES_027_should_work_with_css_selector(page: Page) -> None:
    await page.set_content("<div>hello</div><div>beautiful</div><div>world!</div>")
    divs_count = await page.eval_on_selector_all("css=div", "divs => divs.length")
    assert divs_count == 3


async def test_ES_028_should_work_with_text_selector(page: Page) -> None:
    await page.set_content(
        "<div>hello</div><div>beautiful</div><div>beautiful</div><div>world!</div>"
    )
    divs_count = await page.eval_on_selector_all(
        'text="beautiful"', "divs => divs.length"
    )
    assert divs_count == 2


async def test_ES_029_should_work_with_xpath_selector(page: Page) -> None:
    await page.set_content("<div>hello</div><div>beautiful</div><div>world!</div>")
    divs_count = await page.eval_on_selector_all(
        "xpath=/html/body/div", "divs => divs.length"
    )
    assert divs_count == 3


async def test_ES_030_should_auto_detect_css_selector(page: Page) -> None:
    await page.set_content("<div>hello</div><div>beautiful</div><div>world!</div>")
    divs_count = await page.eval_on_selector_all("div", "divs => divs.length")
    assert divs_count == 3


async def test_ES_031_should_support_syntax(page: Page) -> None:
    await page.set_content(
        "<div><span>hello</span></div><div>beautiful</div><div><span>wo</span><span>rld!</span></div><span>Not this one</span>"
    )
    spans_count = await page.eval_on_selector_all(
        "css=div >> css=span", "spans => spans.length"
    )
    assert spans_count == 3


async def test_ES_032_should_support_capture(page: Page) -> None:
    await page.set_content(
        "<section><div><span>a</span></div></section><section><div><span>b</span></div></section>"
    )
    assert await page.eval_on_selector_all('*css=div >> "b"', "els => els.length") == 1
    assert (
        await page.eval_on_selector_all(
            'section >> *css=div >> "b"', "els => els.length"
        )
        == 1
    )
    assert await page.eval_on_selector_all("section >> *", "els => els.length") == 4

    await page.set_content("<section><div><span>a</span><span>a</span></div></section>")
    assert await page.eval_on_selector_all('*css=div >> "a"', "els => els.length") == 1
    assert (
        await page.eval_on_selector_all(
            'section >> *css=div >> "a"', "els => els.length"
        )
        == 1
    )

    await page.set_content(
        "<div><span>a</span></div><div><span>a</span></div><section><div><span>a</span></div></section>"
    )
    assert await page.eval_on_selector_all('*css=div >> "a"', "els => els.length") == 3
    assert (
        await page.eval_on_selector_all(
            'section >> *css=div >> "a"', "els => els.length"
        )
        == 1
    )


async def test_ES_033_should_support_capture_when_multiple_paths_match(
    page: Page,
) -> None:
    await page.set_content("<div><div><span></span></div></div><div></div>")
    assert await page.eval_on_selector_all("*css=div >> span", "els => els.length") == 2
    await page.set_content(
        "<div><div><span></span></div><span></span><span></span></div><div></div>"
    )
    assert await page.eval_on_selector_all("*css=div >> span", "els => els.length") == 2


async def test_ES_034_should_return_complex_values(page: Page) -> None:
    await page.set_content("<div>hello</div><div>beautiful</div><div>world!</div>")
    texts = await page.eval_on_selector_all(
        "css=div", "divs => divs.map(div => div.textContent)"
    )
    assert texts == ["hello", "beautiful", "world!"]


async def test_ES_035_should_work_with_bogus_array_from(page: Page) -> None:
    await page.set_content("<div>hello</div><div>beautiful</div><div>world!</div>")
    await page.evaluate("() => { Array.from = () => []; }")
    divs_count = await page.eval_on_selector_all("css=div", "divs => divs.length")
    assert divs_count == 3
