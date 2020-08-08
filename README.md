# 🎭 [Playwright](https://github.com/microsoft/playwright) for Python

[![PyPI version](https://badge.fury.io/py/playwright.svg)](https://pypi.python.org/pypi/playwright/) [![Join Slack](https://img.shields.io/badge/join-slack-infomational)](https://join.slack.com/t/playwright/shared_invite/enQtOTEyMTUxMzgxMjIwLThjMDUxZmIyNTRiMTJjNjIyMzdmZDA3MTQxZWUwZTFjZjQwNGYxZGM5MzRmNzZlMWI5ZWUyOTkzMjE5Njg1NDg) <!-- GEN:chromium-version-badge -->[![Chromium version](https://img.shields.io/badge/chromium-86.0.4217.0-blue.svg?logo=google-chrome)](https://www.chromium.org/Home)<!-- GEN:stop --> <!-- GEN:firefox-version-badge -->[![Firefox version](https://img.shields.io/badge/firefox-78.0b5-blue.svg?logo=mozilla-firefox)](https://www.mozilla.org/en-US/firefox/new/)<!-- GEN:stop --> [![WebKit version](https://img.shields.io/badge/webkit-14.0-blue.svg?logo=safari)](https://webkit.org/)

##### [Docs](#documentation) | [API reference](https://github.com/microsoft/playwright/blob/master/docs/api.md)

Playwright is a Python library to automate [Chromium](https://www.chromium.org/Home), [Firefox](https://www.mozilla.org/en-US/firefox/new/) and [WebKit](https://webkit.org/) with a single API. Playwright is built to enable cross-browser web automation that is **ever-green**, **capable**, **reliable** and **fast**.

|          | Linux | macOS | Windows |
|   :---   | :---: | :---: | :---:   |
| Chromium <!-- GEN:chromium-version -->86.0.4217.0<!-- GEN:stop --> | ✅ | ✅ | ✅ |
| WebKit 14.0 | ✅ | ✅ | ✅ |
| Firefox <!-- GEN:firefox-version -->78.0b5<!-- GEN:stop --> | ✅ | ✅ | ✅ |

Headless execution is supported for all the browsers on all platforms.

## Installation

```
pip install playwright
python -m playwright install
```

This installs Playwright and browser binaries for Chromium, Firefox and WebKit. Once installed, you can `import` Playwright in a Python script and automate web browser interactions.

## Capabilities

Playwright is built to automate the broad and growing set of web browser capabilities used by Single Page Apps and Progressive Web Apps.

* Scenarios that span multiple page, domains and iframes
* Auto-wait for elements to be ready before executing actions (like click, fill)
* Intercept network activity for stubbing and mocking network requests
* Emulate mobile devices, geolocation, permissions
* Support for web components via shadow-piercing selectors
* Native input events for mouse and keyboard
* Upload and download files

## Usage

### Pytest

Playwright can be used as a library in your application or as a part of the testing solution. We recommend using our [Pytest plugin](https://github.com/microsoft/playwright-pytest#readme) for testing.

As a library, Playwright offers both blocking (synchronous) API and asyncio API (async/await). You can pick the one that works best for you. They are identical in terms of capabilities and only differ in a way one consumes the API.

Below are some of the examples on how these variations of the API can be used:

#### Sync variant

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

#### Async variant

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

#### Using pytest-playwright

```py
def test_playwright_is_visible_on_google(page):
    page.goto("https://www.google.com")
    page.type("input[name=q]", "Playwright GitHub")
    page.click("input[type=submit]")
    page.waitForSelector("text=microsoft/Playwright")
```

For more information on pytest-playwright, see [GitHub](https://github.com/microsoft/playwright-pytest#readme).

## More examples

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

The asyncio variant:

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

#### Evaluate in browser context

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

The asyncio variant:

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

The asyncio variant:

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

## Documentation

We are in the process of converting the [documentation](https://playwright.dev/) from the Node.js form to the Python one. But you can go ahead and use the Node.js documentation because the API is pretty much the same. You might have noticed that Playwright uses non-Python naming conventions, `camelCase` instead of the `snake_case` for its methods. We recognize that this is not ideal, but it was done deliberately, so that you could rely upon the stack overflow answers and the documentation of the Playwright for Node.js.

### Understanding examples from the JavaScript documentation

You can use all the same methods and arguments as [documented](https://playwright.dev/), just remember that since Python allows named arguments, we didn't need to put `options` parameter into every call as we had to in the Node.js version:

So when you see example like this in JavaScript

```js
await webkit.launch({ headless: false });
```

It translates into Python like this:

```py
webkit.launch(headless=False)
```

If you are using an IDE, it'll suggest parameters that are available in every call.

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

> Note: We don't yet support some of the edge-cases of the vendor-specific APIs such as collecting chromium trace, coverage report, etc.

## Resources

* [Documentation](https://github.com/microsoft/playwright/blob/master/docs/README.md)
* [API reference](https://github.com/microsoft/playwright/blob/master/docs/api.md)
* [Example recipes](https://github.com/microsoft/playwright/blob/master/docs/examples/README.md)
* [Contributing](CONTRIBUTING.md)
