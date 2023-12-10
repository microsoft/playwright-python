import asyncio
from undetected_playwright.async_api import async_playwright, Playwright


async def run(playwright: Playwright):
    args = []
    args.append("--disable-blink-features=AutomationControlled")
    browser = await playwright.chromium.launch( headless=False, args=args)
    page = await browser.new_page()
    await page.goto("https://hmaker.github.io/selenium-detector/")
    await page.evaluate("document")
    await page.evaluate("document.body")
    await page.evaluate("document.documentElement.outerHTML")
    await page.goto("https://nowsecure.nl/#relax")
    await page.evaluate("document")
    res = await page.evaluate("document.documentElement.outerHTML")
    await page.goto("https://abrahamjuliot.github.io/creepjs/")
    await browser.close()


async def main():
    async with async_playwright() as playwright:
        await run(playwright)


if __name__ == "__main__":
    asyncio.run(main())
