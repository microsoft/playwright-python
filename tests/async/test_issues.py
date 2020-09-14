import pytest


@pytest.mark.only_browser("chromium")
async def test_issue_189(browser_type):
    browser = await browser_type.launch(ignoreDefaultArgs=["--mute-audio"])
    page = await browser.newPage()
    assert await page.evaluate("1 + 1") == 2
    await browser.close()
