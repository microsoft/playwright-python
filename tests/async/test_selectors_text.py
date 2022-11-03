import re

from playwright.async_api import Page, expect


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
