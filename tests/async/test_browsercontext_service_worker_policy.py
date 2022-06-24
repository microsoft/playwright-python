from playwright.async_api import Browser
from tests.server import Server


async def test_should_allow_service_workers_by_default(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await page.evaluate("() => window.activationPromise")
    await context.close()


async def test_block_blocks_service_worker_registration(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(service_workers="block")
    page = await context.new_page()
    async with page.expect_console_message(
        lambda m: "Service Worker registration blocked by Playwright" == m.text
    ):
        await page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    await context.close()
