from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = browser_type.launch()
            page = browser.new_page()
            page.goto('http://playwright.dev')
            page.screenshot(path=f'example-{browser_type.name}.png')
            browser.close()


if __name__ == "__main__":
    main()
