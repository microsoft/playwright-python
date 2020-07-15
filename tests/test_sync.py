# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

import pytest

from playwright import Error
from playwright.sync import browser_types, SyncPage


def test_sync_query_selector(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    context = browser.newContext()
    page = context.newPage()
    page.setContent(
        """
    <h1 id="foo">Bar</h1>
    """
    )
    assert (
        page.querySelector("#foo").innerText() == page.querySelector("h1").innerText()
    )
    browser.close()


def test_sync_click(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    page = browser.newPage()
    page.setContent(
        """
    <button onclick="window.clicked=true">Bar</button>
    """
    )
    page.click("text=Bar")
    assert page.evaluate("()=>window.clicked")
    browser.close()


def test_sync_nested_query_selector(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    page = browser.newPage()
    page.setContent(
        """
    <div id="one">
        <span class="two">
            <label>
                MyValue
            </label>
        </span>
    </div>
    """
    )
    e1 = page.querySelector("#one")
    e2 = e1.querySelector(".two")
    e3 = e2.querySelector("label")
    assert e3.innerText() == "MyValue"
    browser.close()


def test_sync_handle_multiple_pages(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    context = browser.newContext()
    page1 = context.newPage()
    page2 = context.newPage()
    assert len(context.pages) == 2
    page1.setContent("one")
    page2.setContent("two")
    assert "one" in page1.content()
    assert "two" in page2.content()
    page1.close()
    assert len(context.pages) == 1
    page2.close()
    assert len(context.pages) == 0
    for page in [page1, page2]:
        with pytest.raises(Error):
            page.content()
    browser.close()


def test_sync_wait_for_selector(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    page = browser.newPage()
    page.evaluate("() => setTimeout(() => document.write('<h1>foo</foo>'), 3 * 1000)")
    page.waitForSelector("h1", timeout=5000)
    browser.close()


def test_sync_wait_for_selector_raise(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    page = browser.newPage()
    page.evaluate("() => setTimeout(() => document.write('<h1>foo</foo>'), 3 * 1000)")
    with pytest.raises(Error) as exc:
        page.waitForSelector("h1", timeout=2000)
    assert "Timeout 2000ms exceeded during" in exc.value.message
    browser.close()


def test_sync_wait_for_event(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    page = browser.newPage()
    page.evaluate(
        "() => setTimeout(() => window.open('https://example.com'), 3 * 1000)"
    )
    page.waitForEvent("popup", timeout=10000)
    browser.close()


def test_sync_make_existing_page_sync(page):
    page = SyncPage(page)
    assert page.evaluate("() => ({'playwright': true})") == {"playwright": True}
    page.setContent("<h1>myElement</h1>")
    page.waitForSelector("text=myElement")


def test_sync_network_events(page, server):
    server.set_route(
        "/hello-world",
        lambda request: (
            request.setHeader("Content-Type", "text/plain"),
            request.write(b"Hello world"),
            request.finish(),
        ),
    )
    page = SyncPage(page)
    page.goto(server.EMPTY_PAGE)
    messages = []
    page.on(
        "request", lambda request: messages.append(f">>{request.method}{request.url}")
    )
    page.on(
        "response",
        lambda response: messages.append(f"<<{response.status}{response.url}"),
    )
    response = page.evaluate("""async ()=> (await fetch("/hello-world")).text()""")
    assert response == "Hello world"
    assert messages == [
        f">>GET{server.PREFIX}/hello-world",
        f"<<200{server.PREFIX}/hello-world",
    ]
