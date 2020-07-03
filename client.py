# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio

from playwright_web import create_playwright

async def run():
    playwright = await create_playwright()

    print('Launching browser...')
    browser = await playwright.webkit.launch(dict(headless=False))
    print('Contexts in browser: %d' % len(browser.contexts))
    print('Creating context...')
    context = await browser.newContext(dict(viewport=None))
    print('Contexts in browser: %d' % len(browser.contexts))
    print('Pages in context: %d' % len(context.pages))

    print('\nCreating page1...')
    page1 = await context.newPage()
    print('Pages in context: %d' % len(context.pages))
    page1.on('framenavigated', lambda frame: print('Frame navigated to %s' % frame.url))
    page1.on('request', lambda request: print('Request %s' % request.url))
    page1.on('requestFinished', lambda request: print('Request finished %s' % request.url))
    page1.on('response', lambda response: print('Response %s, request %s in frame %s' % (response.url, response.request.url, response.frame.url)))
    print('Navigating page1 to https://example.com...')
    await page1.goto('https://example.com')
    print('Page1 main frame url: %s' % page1.mainFrame.url)
    print('Page1 tile: %s' % await page1.title())
    print('Frames in page1: %d' % len(page1.frames))
    # await page1.screenshot(dict(path='example.png'))

    print('\nCreating page2...')
    page2 = await context.newPage()
    page2.on('framenavigated', lambda frame: print('Frame navigated to %s' % frame.url))

    print('Navigating page2 to https://webkit.org...')
    await page2.goto('https://webkit.org')
    print('Page2 tile: %s' % await page2.title())
    print('Pages in context: %d' % len(context.pages))

    print('\nQuerying body...')
    body1 = await page1.querySelector('body')
    print('Body text %s' % await body1.textContent())

    print('Closing page1...')
    await page1.close()
    print('Pages in context: %d' % len(context.pages))

    print('Navigating page2 to https://cnn.com...')
    await page2.goto('https://cnn.com')
    print('Page2 main frame url: %s' % page2.mainFrame.url)
    print('Page2 tile: %s' % await page2.title())
    print('Frames in page2: %d' % len(page2.frames))
    print('Pages in context: %d' % len(context.pages))

    print('Closing context...')
    await context.close()
    print('Contexts in browser: %d' % len(browser.contexts))
    print('Closing browser')
    await browser.close()
    await playwright.dispose()

asyncio.run(run())
