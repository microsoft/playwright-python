# 🎭 [Playwright](https://playwright.dev) for Python [![PyPI version](https://badge.fury.io/py/playwright.svg)](https://pypi.python.org/pypi/playwright/) [![Join Slack](https://img.shields.io/badge/join-slack-infomational)](https://join.slack.com/t/playwright/shared_invite/enQtOTEyMTUxMzgxMjIwLThjMDUxZmIyNTRiMTJjNjIyMzdmZDA3MTQxZWUwZTFjZjQwNGYxZGM5MzRmNzZlMWI5ZWUyOTkzMjE5Njg1NDg)

#### [Docs](#documentation) | [Website](https://playwright.dev/) | [Python API reference](https://microsoft.github.io/playwright-python/)

Playwright is a Python library to automate [Chromium](https://www.chromium.org/Home), [Firefox](https://www.mozilla.org/en-US/firefox/new/) and [WebKit](https://webkit.org/) browsers with a single API. Playwright delivers automation that is **ever-green**, **capable**, **reliable** and **fast**. [See how Playwright is better](https://playwright.dev/#path=docs%2Fwhy-playwright.md&q=).

|          | Linux | macOS | Windows |
|   :---   | :---: | :---: | :---:   |
| Chromium <!-- GEN:chromium-version -->86.0.4238.0<!-- GEN:stop --> | ✅ | ✅ | ✅ |
| WebKit 14.0 | ✅ | ✅ | ✅ |
| Firefox <!-- GEN:firefox-version -->80.0b8<!-- GEN:stop --> | ✅ | ✅ | ✅ |

Headless execution is supported for all the browsers on all platforms.

* [Usage](#usage)
  - [Sync API](#sync-api)
  - [Async API](#async-api)
  - [With pytest](#with-pytest)
  - [Interactive mode (REPL)](#interactive-mode-repl)
* [Examples](#examples)
  - [Mobile and geolocation](#mobile-and-geolocation)
  - [Evaluate JS in browser](#evaluate-js-in-browser)
  - [Intercept network requests](#intercept-network-requests)
* [Documentation](#documentation)

## Usage

```
pip install playwright
python -m playwright install
```

This installs Playwright and browser binaries for Chromium, Firefox and WebKit. Playwright requires Python 3.7+.

Playwright offers both sync (blocking) API and async API. They are identical in terms of capabilities and only differ in how one consumes the API.

#### Sync API

```py
from playwright import sync_playwright

with sync_playwright() as p:
    for browser_type in [p.chromium, p.firefox, p.webkit]:
        browser = browser_type.launch()
        page = browser.newPage()
        page.goto('http://whatsmyuseragent.org/')
        page.screenshot(path=f'example-{browser_type.name}.png')
        browser.close()
```

#### Async API

```py
import asyncio
from playwright import async_playwright

async def main():
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch()
            page = await browser.newPage()
            await page.goto('http://whatsmyuseragent.org/')
            await page.screenshot(path=f'example-{browser_type.name}.png')
            await browser.close()

asyncio.get_event_loop().run_until_complete(main())
```

#### With pytest

Use our [pytest plugin for Playwright](https://github.com/microsoft/playwright-pytest#readme).

```py
def test_playwright_is_visible_on_google(page):
    page.goto("https://www.google.com")
    page.type("input[name=q]", "Playwright GitHub")
    page.click("input[type=submit]")
    page.waitForSelector("text=microsoft/Playwright")
```

#### Interactive mode (REPL)

```py
>>> from playwright import sync_playwright
>>> playwright = sync_playwright().start()

# Use playwright.chromium, playwright.firefox or playwright.webkit
# Pass headless=False to see the browser UI
>>> browser = playwright.chromium.launch()
>>> page = browser.newPage()
>>> page.goto("http://whatsmyuseragent.org/")
>>> page.screenshot(path="example.png")
>>> browser.close()
>>> playwright.stop()
```

## Examples

#### Mobile and geolocation

This snippet emulates Mobile Safari on a device at a given geolocation, navigates to maps.google.com, performs action and takes a screenshot.

```py
from playwright import sync_playwright

with sync_playwright() as p:
    iphone_11 = p.devices['iPhone 11 Pro']
    browser = p.webkit.launch(headless=False)
    context = browser.newContext(
        **iphone_11,
        locale='en-US',
        geolocation={ 'longitude': 12.492507, 'latitude': 41.889938 },
        permissions=['geolocation']
    )
    page = context.newPage()
    page.goto('https://maps.google.com')
    page.click('text="Your location"')
    page.screenshot(path='colosseum-iphone.png')
    browser.close()
```

<details>
<summary>Async variant</summary>

```py
import asyncio
from playwright import async_playwright

async def main():
    async with async_playwright() as p:
        iphone_11 = p.devices['iPhone 11 Pro']
        browser = await p.webkit.launch(headless=False)
        context = await browser.newContext(
            **iphone_11,
            locale='en-US',
            geolocation={ 'longitude': 12.492507, 'latitude': 41.889938 },
            permissions=['geolocation']
        )
        page = await context.newPage()
        await page.goto('https://maps.google.com')
        await page.click('text="Your location"')
        await page.screenshot(path='colosseum-iphone.png')
        await browser.close()

asyncio.get_event_loop().run_until_complete(main())
```
</details>

#### Evaluate JS in browser

This code snippet navigates to example.com in Firefox, and executes a script in the page context.

```py
from playwright import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch()
    page = browser.newPage()
    page.goto('https://www.example.com/')
    dimensions = page.evaluate('''() => {
      return {
        width: document.documentElement.clientWidth,
        height: document.documentElement.clientHeight,
        deviceScaleFactor: window.devicePixelRatio
      }
    }''')
    print(dimensions)
    browser.close()
```
<details>
<summary>Async variant</summary>

```py
import asyncio
from playwright import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch()
        page = await browser.newPage()
        await page.goto('https://www.example.com/')
        dimensions = await page.evaluate('''() => {
          return {
            width: document.documentElement.clientWidth,
            height: document.documentElement.clientHeight,
            deviceScaleFactor: window.devicePixelRatio
          }
        }''')
        print(dimensions)
        await browser.close()

asyncio.get_event_loop().run_until_complete(main())
```
</details>

#### Intercept network requests

This code snippet sets up request routing for a Chromium page to log all network requests.

```py
from playwright import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.newPage()

    def log_and_continue_request(route, request):
      print(request.url)
      route.continue_()

    # Log and continue all network requests
    page.route('**', lambda route, request: log_and_continue_request(route, request))

    page.goto('http://todomvc.com')
    browser.close()
```
<details>
<summary>Async variant</summary>

```py
import asyncio
from playwright import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.newPage()

        def log_and_continue_request(route, request):
            print(request.url)
            asyncio.create_task(route.continue_())

        # Log and continue all network requests
        await page.route('**', lambda route, request: log_and_continue_request(route, request))

        await page.goto('http://todomvc.com')
        await browser.close()

asyncio.get_event_loop().run_until_complete(main())
```
</details>

## Documentation

We are in the process of converting our [documentation](https://playwright.dev/) from the Node.js form to Python. You can go ahead and use the Node.js documentation since the API is pretty much the same. Playwright uses non-Python naming conventions (`camelCase` instead of `snake_case`) for its methods. We recognize that this is not ideal, but it was done deliberately, so that you could rely upon Stack Overflow answers and existing documentation.

### Named arguments

Since Python allows named arguments, we didn't need to put the `options` parameter into every call as in the Node.js API. So when you see example like this in JavaScript

```js
await webkit.launch({ headless: false });
```

It translates into Python like this:

```py
webkit.launch(headless=False)
```

If you are using an IDE, it will suggest parameters that are available in every call.

### Evaluating functions

Another difference is that in the JavaScript version, `page.evaluate` accepts JavaScript functions, while this does not make any sense in the Python version.

In JavaScript it will be documented as:

```js
const result = await page.evaluate(([x, y]) => {
  return Promise.resolve(x * y);
}, [7, 8]);
console.log(result); // prints "56"
```

And in Python that would look like:

```py
result = page.evaluate("""
    ([x, y]) => {
        return Promise.resolve(x * y);
    }""",
    [7, 8])
print(result) # prints "56"
```

The library will detect that what are passing it is a function and will invoke it with the given parameters. You can opt out of this function detection and pass `force_expr=True` to all evaluate functions, but you probably will never need to do that.

### Using context managers

Python enabled us to do some of the things that were not possible in the Node.js version and we used the opportunity. Instead of using the `page.waitFor*` methods, we recommend using corresponding `page.expect_*` context manager.

In JavaScript it will be documented as:

```js
const [ download ] = await Promise.all([
  page.waitForEvent('download'), // <-- start waiting for the download
  page.click('button#delayed-download') // <-- perform the action that directly or indirectly initiates it.
]);
const path = await download.path();
```

And in Python that would look much simpler:

```py
with page.expect_download() as download_info:
    page.click("button#delayed-download")
download = download_info.value
path = download.path()
```

Similarly, for waiting for the network response:

```js
const [response] = await Promise.all([
  page.waitForResponse('**/api/fetch_data'),
  page.click('button#update'),
]);
```

Becomes

```py
with page.expect_response("**/api/fetch_data"):
    page.click("button#update")
```

## Is Playwright for Python ready?

Yes, Playwright for Python is ready. We are still not at the version v1.0, so minor breaking API changes could potentially happen. But a) this is unlikely and b) we will only do that if we know it improves your experience with the new library. We'd like to collect your feedback before we freeze the API for v1.0.

> Note: We don't yet support some of the edge-cases of the vendor-specific APIs such as collecting Chromium trace, coverage report, etc.
