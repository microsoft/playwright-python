import re

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    r = open("README.md", "r")
    text = r.read()
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        rx = re.compile(
            r"<!-- GEN:" + browser_type.name + r"-version -->([^<]+)<!-- GEN:stop -->"
        )
        browser = browser_type.launch()
        text = rx.sub(
            f"<!-- GEN:{browser_type.name}-version -->{browser.version}<!-- GEN:stop -->",
            text,
        )
        browser.close()

    w = open("README.md", "w")
    w.write(text)
    w.close()
