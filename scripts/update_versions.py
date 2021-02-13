import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as p:
        readme = Path("README.md").resolve()
        text = readme.read_text(encoding="utf-8")
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            rx = re.compile(
                r"<!-- GEN:"
                + browser_type.name
                + r"-version -->([^<]+)<!-- GEN:stop -->"
            )
            browser = browser_type.launch()
            text = rx.sub(
                f"<!-- GEN:{browser_type.name}-version -->{browser.version}<!-- GEN:stop -->",
                text,
            )
            browser.close()
        readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
