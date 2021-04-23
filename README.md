# 🎭 [Playwright](https://playwright.dev) for Python [![PyPI version](https://badge.fury.io/py/playwright.svg)](https://pypi.python.org/pypi/playwright/) [![Join Slack](https://img.shields.io/badge/join-slack-infomational)](https://aka.ms/playwright-slack)

#### [Docs](https://playwright.dev/python/docs/intro) | [API](https://playwright.dev/python/docs/api/class-playwright)

Playwright is a Python library to automate [Chromium](https://www.chromium.org/Home), [Firefox](https://www.mozilla.org/en-US/firefox/new/) and [WebKit](https://webkit.org/) browsers with a single API. Playwright delivers automation that is **ever-green**, **capable**, **reliable** and **fast**. [See how Playwright is better](https://playwright.dev/python/docs/why-playwright).

|          | Linux | macOS | Windows |
|   :---   | :---: | :---: | :---:   |
| Chromium <!-- GEN:chromium-version -->91.0.4469.0<!-- GEN:stop --> | ✅ | ✅ | ✅ |
| WebKit <!-- GEN:webkit-version -->14.2<!-- GEN:stop --> | ✅ | ✅ | ✅ |
| Firefox <!-- GEN:firefox-version -->88.0b8<!-- GEN:stop --> | ✅ | ✅ | ✅ |

Headless execution is supported for all browsers on all platforms.

- [Usage](#usage)
  - [Record and generate code](#record-and-generate-code)
  - [Sync API](#sync-api)
  - [Async API](#async-api)
  - [With pytest](#with-pytest)
  - [Interactive mode (REPL)](#interactive-mode-repl)
- [Examples](#examples)
  - [Mobile and geolocation](#mobile-and-geolocation)
  - [Evaluate JS in browser](#evaluate-js-in-browser)
  - [Intercept network requests](#intercept-network-requests)
- [Documentation](#documentation)

## Usage

```sh
pip install playwright
playwright install
```

This installs Playwright and browser binaries for Chromium, Firefox and WebKit. Playwright requires Python 3.7+.

#### Record and generate code

Playwright can record user interactions in a browser and generate code. [See demo](https://user-images.githubusercontent.com/284612/95930164-ad52fb80-0d7a-11eb-852d-04bfd19de800.gif).

```sh
# Pass --help to see all options
playwright codegen
```

Playwright offers both sync (blocking) API and async API. They are identical in terms of capabilities and only differ in how one consumes the API.

#### Sync API

This is our default API for short snippets and tests. If you are not using asyncio in your
application, it is the easiest to use Sync API notation.

```py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        browser = browser_type.launch()
        page = browser.new_page()
        page.goto('http://whatsmyuseragent.org/')
        page.screenshot(path=f'example-{browser_type.name}.png')
        browser.close()
```

#### Async API

If your app is based on the modern asyncio loop and you are used to async/await constructs,
Playwright exposes Async API for you. You should use this API inside a Python REPL supporting `asyncio` like with `python -m asyncio`

```console
$ python -m asyncio
```

```py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            page = await browser.new_page()
            await page.goto('http://whatsmyuseragent.org/')
            await page.screenshot(path=f'example-{browser_type.name}.png')
            await browser.close()

asyncio.run(main())
```

#### With pytest

Use our [pytest plugin for Playwright](https://github.com/microsoft/playwright-pytest#readme).

```py
def test_playwright_is_visible_on_google(page):
    page.goto("https://www.google.com")
    page.type("input[name=q]", "Playwright GitHub")
    page.click("input[type=submit]")
    page.wait_for_selector("text=microsoft/Playwright")
```

#### Interactive mode (REPL)

Blocking REPL, as in CLI:

```py
>>> from playwright.sync_api import sync_playwright
>>> playwright = sync_playwright().start()

# Use playwright.chromium, playwright.firefox or playwright.webkit
# Pass headless=False to see the browser UI
>>> browser = playwright.chromium.launch()
>>> page = browser.new_page()
>>> page.goto("http://whatsmyuseragent.org/")
>>> page.screenshot(path="example.png")
>>> browser.close()
>>> playwright.stop()
```

Async REPL such as `asyncio` REPL:

```console
$ python -m asyncio
```

```py
>>> from playwright.async_api import async_playwright
>>> playwright = await async_playwright().start()
>>> browser = await playwright.chromium.launch()
>>> page = await browser.new_page()
>>> await page.goto("http://whatsmyuseragent.org/")
>>> await page.screenshot(path="example.png")
>>> await browser.close()
>>> await playwright.stop()
```

## Examples

#### Mobile and geolocation

This snippet emulates Mobile Safari on a device at a given geolocation, navigates to maps.google.com, performs action and takes a screenshot.

```py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    iphone_11 = p.devices["iPhone 11 Pro"]
    browser = p.webkit.launch(headless=False)
    context = browser.new_context(
        **iphone_11,
        locale="en-US",
        geolocation={"longitude": 12.492507, "latitude": 41.889938 },
        permissions=["geolocation"]
    )
    page = context.new_page()
    page.goto("https://maps.google.com")
    page.click("text=Your location")
    page.screenshot(path="colosseum-iphone.png")
    browser.close()
```

<details>
<summary>Async variant</summary>

```py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        iphone_11 = p.devices["iPhone 11 Pro"]
        browser = await p.webkit.launch(headless=False)
        context = await browser.new_context(
            **iphone_11,
            locale="en-US",
            geolocation={"longitude": 12.492507, "latitude": 41.889938},
            permissions=["geolocation"]
        )
        page = await context.newPage()
        await page.goto("https://maps.google.com")
        await page.click("text="Your location"")
        await page.screenshot(path="colosseum-iphone.png")
        await browser.close()

asyncio.run(main())
```

</details>

#### Evaluate JS in browser

This code snippet navigates to example.com in Firefox, and executes a script in the page context.

```py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch()
    page = browser.new_page()
    page.goto("https://www.example.com/")
    dimensions = page.evaluate("""() => {
      return {
        width: document.documentElement.clientWidth,
        height: document.documentElement.clientHeight,
        deviceScaleFactor: window.devicePixelRatio
      }
    }""")
    print(dimensions)
    browser.close()
```

<details>
<summary>Async variant</summary>

```py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        page = await browser.new_page()
        await page.goto("https://www.example.com/")
        dimensions = await page.evaluate("""() => {
          return {
            width: document.documentElement.clientWidth,
            height: document.documentElement.clientHeight,
            deviceScaleFactor: window.devicePixelRatio
          }
        }""")
        print(dimensions)
        await browser.close()

asyncio.run(main())
```

</details>

#### Intercept network requests

This code snippet sets up request routing for a Chromium page to log all network requests.

```py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    def log_and_continue_request(route, request):
        print(request.url)
        route.continue_()

    # Log and continue all network requests
    page.route("**/*", log_and_continue_request)

    page.goto("http://todomvc.com")
    browser.close()
```

<details>
<summary>Async variant</summary>

```py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        async def log_and_continue_request(route, request):
            print(request.url)
            await route.continue_()

        # Log and continue all network requests
        await page.route("**/*", log_and_continue_request)
        await page.goto("http://todomvc.com")
        await browser.close()

asyncio.run(main())
```

</details>

## Documentation

Check out our [new documentation site](https://playwright.dev/python/docs/intro)!
