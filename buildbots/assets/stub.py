from playwright import sync_playwright

with sync_playwright() as p:
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        browser = browser_type.launch()
        page = browser.newPage()
        page.setContent("<h1>Test 123</h1>")
        page.screenshot(path=f"{browser_type.name}.png")
        browser.close()
