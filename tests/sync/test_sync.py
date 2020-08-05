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

import os

import pytest

from playwright import Error, TimeoutError, sync_playwright
from playwright.sync_api import Browser, Page


def test_sync_query_selector(page):
    page.setContent(
        """
    <h1 id="foo">Bar</h1>
    """
    )
    assert (
        page.querySelector("#foo").innerText() == page.querySelector("h1").innerText()
    )


def test_sync_click(page):
    page.setContent(
        """
    <button onclick="window.clicked=true">Bar</button>
    """
    )
    page.click("text=Bar")
    assert page.evaluate("()=>window.clicked")


def test_sync_nested_query_selector(page):
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


def test_sync_handle_multiple_pages(context):
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


def test_sync_wait_for_event(page: Page, server):
    with page.expect_event("popup", timeout=10000) as popup:
        page.evaluate("(url) => window.open(url)", server.EMPTY_PAGE)
    assert popup.value


def test_sync_wait_for_event_raise(page):
    with pytest.raises(Error):
        with page.expect_event("popup", timeout=500) as popup:
            assert False
        assert popup.value is None


def test_sync_make_existing_page_sync(page):
    page = page
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


def test_console_should_work(page):
    messages = []
    page.once("console", lambda m: messages.append(m))
    page.evaluate('() => console.log("hello", 5, {foo: "bar"})'),
    assert len(messages) == 1
    message = messages[0]
    assert message.text == "hello 5 JSHandle@object"
    assert str(message) == "hello 5 JSHandle@object"
    assert message.type == "log"
    assert message.args[0].jsonValue() == "hello"
    assert message.args[1].jsonValue() == 5
    assert message.args[2].jsonValue() == {"foo": "bar"}


def test_sync_download(browser: Browser, server):
    server.set_route(
        "/downloadWithFilename",
        lambda request: (
            request.setHeader("Content-Type", "application/octet-stream"),
            request.setHeader("Content-Disposition", "attachment; filename=file.txt"),
            request.write(b"Hello world"),
            request.finish(),
        ),
    )
    page = browser.newPage(acceptDownloads=True)
    page.setContent(f'<a href="{server.PREFIX}/downloadWithFilename">download</a>')

    with page.expect_event("download") as download:
        page.click("a")
    assert download.value
    assert download.value.suggestedFilename == "file.txt"
    path = download.value.path()
    assert os.path.isfile(path)
    with open(path, "r") as fd:
        assert fd.read() == "Hello world"
    page.close()


def test_sync_workers_page_workers(page: Page, server):
    with page.expect_event("worker") as event_worker:
        page.goto(server.PREFIX + "/worker/worker.html")
    assert event_worker.value
    worker = page.workers[0]
    assert "worker.js" in worker.url

    assert worker.evaluate('() => self["workerFunction"]()') == "worker function result"

    page.goto(server.EMPTY_PAGE)
    assert len(page.workers) == 0


def test_sync_playwright_multiple_times():
    with sync_playwright() as pw1:
        assert pw1.chromium
        with pytest.raises(Error) as exc:
            with sync_playwright() as pw2:
                assert pw1.chromium == pw2.chromium
        assert "Can only run one Playwright at a time." in exc.value.message


def test_sync_set_default_timeout(page):
    page.setDefaultTimeout(1)
    with pytest.raises(TimeoutError) as exc:
        page.waitForFunction("false")
    assert "Timeout 1ms exceeded." in exc.value.message


def test_close_should_reject_all_promises(context):
    new_page = context.newPage()
    with pytest.raises(Error) as exc_info:
        new_page._gather(
            lambda: new_page.evaluate("() => new Promise(r => {})"),
            lambda: new_page.close(),
        )
    assert "Protocol error" in exc_info.value.message


def test_expect_response_should_work(page: Page, server):
    with page.expect_response("**/*") as resp:
        page.goto(server.EMPTY_PAGE)
    assert resp.value
    assert resp.value.url == server.EMPTY_PAGE
    assert resp.value.status == 200
    assert resp.value.ok
    assert resp.value.request
