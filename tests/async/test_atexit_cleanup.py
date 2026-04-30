import asyncio

from playwright.async_api import async_playwright


async def test_stop_during_concurrent_operations() -> None:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch()
    
    async def quick_operation():
        try:
            page = await browser.new_page()
            await page.close()
        except Exception:
            pass
    
    task = asyncio.create_task(quick_operation())
    await asyncio.sleep(0.01)
    await playwright.stop()
    
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        raise AssertionError("Playwright.stop() deadlocked during concurrent operations")
