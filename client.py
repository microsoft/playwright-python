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

import playwright
from playwright.sync_api import Playwright


def main(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page(viewport=0)
    page.set_content(
        "<button id=button onclick=\"window.open('http://webkit.org', '_blank')\">Click me</input>"
    )

    with page.expect_popup() as popup_info:
        page.click("#button")
    print(popup_info.value)

    print("Contexts in browser: %d" % len(browser.contexts))
    print("Creating context...")
    context = browser.new_context(viewport=0)
    print("Contexts in browser: %d" % len(browser.contexts))
    print("Pages in context: %d" % len(context.pages))

    print("\nCreating page1...")
    page1 = context.new_page()
    print("Pages in context: %d" % len(context.pages))
    page1.on("framenavigated", lambda frame: print("Frame navigated to %s" % frame.url))
    page1.on("request", lambda request: print("Request %s" % request.url))
    page1.on(
        "requestFinished", lambda request: print("Request finished %s" % request.url)
    )
    page1.on(
        "response",
        lambda response: print(
            "Response %s, request %s in frame %s"
            % (response.url, response.request.url, response.frame.url)
        ),
    )
    print("Navigating page1 to https://example.com...")
    page1.goto("https://example.com")
    print("Page1 main frame url: %s" % page1.main_frame.url)
    print("Page1 tile: %s" % page1.title())
    print("Frames in page1: %d" % len(page1.frames))
    page1.screenshot(path="example.png")

    print("\nCreating page2...")
    page2 = context.new_page()
    page2.on("framenavigated", lambda frame: print("Frame navigated to %s" % frame.url))

    print("Navigating page2 to https://webkit.org...")
    page2.goto("https://webkit.org")
    print("Page2 tile: %s" % page2.title())
    print("Pages in context: %d" % len(context.pages))

    print("\nQuerying body...")
    body1 = page1.query_selector("body")
    assert body1
    print("Body text %s" % body1.text_content())

    print("Closing page1...")
    page1.close()
    print("Pages in context: %d" % len(context.pages))

    print("Navigating page2 to https://cnn.com...")
    page2.goto("https://cnn.com")
    print("Page2 main frame url: %s" % page2.main_frame.url)
    print("Page2 tile: %s" % page2.title())
    print("Frames in page2: %d" % len(page2.frames))
    print("Pages in context: %d" % len(context.pages))

    print("Closing context...")
    context.close()
    print("Contexts in browser: %d" % len(browser.contexts))
    print("Closing browser")
    browser.close()


if __name__ == "__main__":
    with playwright.sync_api.sync_playwright() as p:
        main(p)
