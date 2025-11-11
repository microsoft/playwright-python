# 🎭 [Playwright](https://playwright.dev) for Python 
[![PyPI version](https://badge.fury.io/py/playwright.svg)](https://pypi.python.org/pypi/playwright/) 
[![Anaconda version](https://img.shields.io/conda/v/microsoft/playwright)](https://anaconda.org/Microsoft/playwright) 
[![Join Discord](https://img.shields.io/badge/join-discord-infomational)](https://aka.ms/playwright/discord)

Playwright is a powerful Python library to automate [Chromium](https://www.chromium.org/Home), [Firefox](https://www.mozilla.org/en-US/firefox/new/) and [WebKit](https://webkit.org/) browsers with a single API. Playwright delivers automation that is **ever-green**, **capable**, **reliable** and **fast**. [See how Playwright is better](https://playwright.dev/python).

## 🌟 Key Features

- **Cross-browser**: Automate Chromium, Firefox, and WebKit with the same API
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Cross-language**: Same API available in Python, JavaScript, .NET, and Java
- **Auto-waiting**: Automatically waits for elements to be ready
- **Mobile emulation**: Test responsive web apps with mobile device simulation
- **Network interception**: Capture and modify network requests
- **Reliable selectors**: Built-in support for text, CSS, XPath, and React selectors

## 🚀 Quick Start

### Installation

```bash
# Install Playwright
pip install playwright

# Install browser binaries (Chrome, Firefox, WebKit)
playwright install
```

### Your First Script

Create a file `example.py`:

```python
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('https://playwright.dev')
        page.screenshot(path='example.png')
        print(f"Page title: {page.title()}")
        browser.close()

if __name__ == "__main__":
    main()
```

Run your script:
```bash
python example.py
```

## 📚 Examples

### Sync API

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        browser = browser_type.launch()
        page = browser.new_page()
        page.goto('http://playwright.dev')
        page.screenshot(path=f'example-{browser_type.name}.png')
        print(f"Screenshot saved: example-{browser_type.name}.png")
        browser.close()
```

### Async API

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            page = await browser.new_page()
            await page.goto('http://playwright.dev')
            await page.screenshot(path=f'example-{browser_type.name}.png')
            print(f"Screenshot saved: example-{browser_type.name}.png")
            await browser.close()

asyncio.run(main())
```

## 🛠️ Installation Guide

### Prerequisites
- Python 3.7 or higher
- pip package manager
- Node.js 14 or higher

### Step-by-Step Setup

1. **Create virtual environment** (recommended):
   ```bash
   python -m venv playwright-env
   source playwright-env/bin/activate
   ```

2. **Install Playwright**:
   ```bash
   pip install playwright
   ```

3. **Install browsers**:
   ```bash
   playwright install
   ```

### Installation Options

- **Specific browser**:
  ```bash
  playwright install chromium
  playwright install firefox
  ```

- **With conda**:
  ```bash
  conda install -c conda-forge playwright
  ```

## 🌐 Supported Browsers

| Browser   | Linux | macOS | Windows |
|-----------|-------|-------|---------|
| Chromium  |  ✅  |  ✅   |   ✅   |
| WebKit    |  ✅  |  ✅   |   ✅   | 
| Firefox   |  ✅  |  ✅   |   ✅   |

## ❓ Troubleshooting

**"playwright: command not found"**
- Use: `python -m playwright` instead of `playwright`

**Browser installation fails**
- Check internet connection
- Try: `playwright install --force`

**Permission errors**
- Use: `sudo playwright install`

## 📖 Learning Resources

- [Documentation](https://playwright.dev/python/docs/intro)
- [API Reference](https://playwright.dev/python/docs/api/class-playwright)
- [Examples](https://playwright.dev/python/docs/examples)

## 🌍 Other Languages

- [Node.js](https://playwright.dev/docs/intro)
- [.NET](https://playwright.dev/dotnet/docs/intro)
- [Java](https://playwright.dev/java/docs/intro)

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding new features, or improving documentation, your help is appreciated.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Contribution Guidelines

- Follow the existing code style
- Add tests for new functionality
- Update documentation for changes
- Ensure all tests pass
- Be respectful and constructive in discussions

### Getting Help

- 📖 Read our [Contributing Guide](CONTRIBUTING.md)
- 💬 Join the [Discord Community](https://aka.ms/playwright/discord)
- 🐛 Report issues on [GitHub Issues](https://github.com/microsoft/playwright-python/issues)

---

**Happy testing!** 🎭
