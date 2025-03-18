import asyncio
from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            page = await browser.new_page()
            await page.goto('http://playwright.dev')
            await page.screenshot(path=f'example-{browser_type.name}.png')
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
