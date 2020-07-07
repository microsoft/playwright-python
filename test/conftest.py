import playwright_web
import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = playwright_web.playwright.loop
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    browser = await playwright_web.chromium.launch()
    yield browser
    await browser.close()


@pytest.fixture
async def context(browser):
    context = await browser.newContext()
    yield context
    await context.close()

@pytest.fixture
async def page(context):
    page = await context.newPage()
    yield page
    await page.close()
