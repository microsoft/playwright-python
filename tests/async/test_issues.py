import pytest


@pytest.mark.only_browser("chromium")
async def test_issue_189(browser_type):
    browser = await browser_type.launch(ignoreDefaultArgs=["--mute-audio"])
    page = await browser.newPage()
    assert await page.evaluate("1 + 1") == 2
    await browser.close()


@pytest.mark.only_browser("chromium")
async def test_issue_195(playwright, browser):
    iphone_11 = playwright.devices["iPhone 11"]
    context = await browser.newContext(**iphone_11)
    await context.close()
