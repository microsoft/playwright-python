# 🎭 Playwright for Python

[![PyPI version](https://badge.fury.io/py/playwright.svg)](https://pypi.python.org/pypi/playwright/) [![Join Slack](https://img.shields.io/badge/join-slack-infomational)](https://join.slack.com/t/playwright/shared_invite/enQtOTEyMTUxMzgxMjIwLThjMDUxZmIyNTRiMTJjNjIyMzdmZDA3MTQxZWUwZTFjZjQwNGYxZGM5MzRmNzZlMWI5ZWUyOTkzMjE5Njg1NDg) <!-- GEN:chromium-version-badge -->[![Chromium version](https://img.shields.io/badge/chromium-85.0.4182.0-blue.svg?logo=google-chrome)](https://www.chromium.org/Home)<!-- GEN:stop --> <!-- GEN:firefox-version-badge -->[![Firefox version](https://img.shields.io/badge/firefox-78.0b5-blue.svg?logo=mozilla-firefox)](https://www.mozilla.org/en-US/firefox/new/)<!-- GEN:stop --> [![WebKit version](https://img.shields.io/badge/webkit-14.0-blue.svg?logo=safari)](https://webkit.org/)
[![Coverage Status](https://coveralls.io/repos/github/microsoft/playwright-python/badge.svg?branch=master)](https://coveralls.io/github/microsoft/playwright-python?branch=master)

##### [Docs](https://github.com/microsoft/playwright/blob/master/docs/README.md) | [API reference](https://github.com/microsoft/playwright/blob/master/docs/api.md)

Playwright is a Python library to automate [Chromium](https://www.chromium.org/Home), [Firefox](https://www.mozilla.org/en-US/firefox/new/) and [WebKit](https://webkit.org/) with a single API. Playwright is built to enable cross-browser web automation that is **ever-green**, **capable**, **reliable** and **fast**.

|          | Linux | macOS | Windows |
|   :---   | :---: | :---: | :---:   |
| Chromium <!-- GEN:chromium-version -->85.0.4182.0<!-- GEN:stop --> | ✅ | ✅ | ✅ |
| WebKit 14.0 | ✅ | ✅ | ✅ |
| Firefox <!-- GEN:firefox-version -->78.0b5<!-- GEN:stop --> | ✅ | ✅ | ✅ |

Headless execution is supported for all the browsers on all platforms.

This is a Python 3 version of the [https://github.com/microsoft/playwright](https://github.com/microsoft/playwright) project.

## Usage

```
pip install playwright
```

This installs Playwright and browser binaries for Chromium, Firefox and WebKit. Once installed, you can `import` Playwright in a Python script and automate web browser interactions.

* [Getting started](https://github.com/microsoft/playwright/blob/master/docs/intro.md)
* [Installation configuration](https://github.com/microsoft/playwright/blob/master/docs/installation.md)
* [API reference](https://github.com/microsoft/playwright/blob/master/docs/api.md)

## Capabilities

Playwright is built to automate the broad and growing set of web browser capabilities used by Single Page Apps and Progressive Web Apps.

* Scenarios that span multiple page, domains and iframes
* Auto-wait for elements to be ready before executing actions (like click, fill)
* Intercept network activity for stubbing and mocking network requests
* Emulate mobile devices, geolocation, permissions
* Support for web components via shadow-piercing selectors
* Native input events for mouse and keyboard
* Upload and download files

## Examples

#### Page screenshot

This code snippet navigates to whatsmyuseragent.org in Chromium, Firefox and WebKit, and saves 3 screenshots.

```py
import asyncio
from playwright import chromium, firefox, webkit

async def run():
  for browser_type in [chromium, firefox, webkit]:
    browser = await browser_type.launch()
    page = await browser.newPage()
    await page.goto('http://whatsmyuseragent.org/')
    await page.screenshot(path=f'example-{browser_type.name}.png')
    await browser.close()

asyncio.get_event_loop().run_until_complete(run())
```

#### Mobile and geolocation

This snippet emulates Mobile Safari on a device at a given geolocation, navigates to maps.google.com, performs action and takes a screenshot.

```py
import asyncio
from playwright import webkit, devices

iphone_11 = devices['iPhone 11 Pro']
print(iphone_11)

async def run():
  browser = await webkit.launch(headless=False)
  context = await browser.newContext(
    **iphone_11,
    locale='en-US',
    geolocation={ 'longitude': 12.492507, 'latitude': 41.889938 },
    permissions=['geolocation']
  )
  page = await context.newPage()
  await page.goto('https://maps.google.com')
  await page.click('text="Your location"')
  await page.waitForRequest('*preview/pwa')
  await page.screenshot(path='colosseum-iphone.png')
  await browser.close()

asyncio.get_event_loop().run_until_complete(run())
```

#### Evaluate in browser context

This code snippet navigates to example.com in Firefox, and executes a script in the page context.

```py
import asyncio
from playwright import firefox

async def run():
  browser = await firefox.launch()
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

asyncio.get_event_loop().run_until_complete(run())
```

#### Intercept network requests

This code snippet sets up request routing for a Chromium page to log all network requests.

```py
import asyncio
from playwright import chromium

async def run():
  browser = await chromium.launch()
  page = await browser.newPage()

  async def log_and_continue_request(route, request):
    print(request.url)
    await route.continue_()

  # Log and continue all network requests
  await page.route('**', lambda route, request: asyncio.ensure_future(log_and_continue_request(route, request)))

  await page.goto('http://todomvc.com')
  await browser.close()

asyncio.get_event_loop().run_until_complete(run())
```

# Is Playwright for Python ready?

We are ready for your feedback, but we are still covering Playwright Python with the tests, so expect a bumpy ride and don't use for production.

## Resources

* [Documentation](https://github.com/microsoft/playwright/blob/master/docs/README.md)
* [API reference](https://github.com/microsoft/playwright/blob/master/docs/api.md)
* [Example recipes](https://github.com/microsoft/playwright/blob/master/docs/examples/README.md)
* [Contributing](CONTRIBUTING.md)
