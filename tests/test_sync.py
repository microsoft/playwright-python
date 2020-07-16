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
import os

from playwright import Error
from playwright.sync import (
    SyncConsoleMessage,
    SyncDownload,
    SyncWorker,
    browser_types,
    SyncPage,
)


@pytest.fixture(scope="session")
def sync_browser(browser_name, launch_arguments):
    browser = browser_types[browser_name].launch(**launch_arguments)
    yield browser
    browser.close()


@pytest.fixture
def sync_context(sync_browser):
    context = sync_browser.newContext()
    yield context
    context.close()


@pytest.fixture
def sync_page(sync_context):
    page = sync_context.newPage()
    yield page
    page.close()


def test_sync_query_selector(sync_page):
    sync_page.setContent(
        """
    <h1 id="foo">Bar</h1>
    """
    )
    assert (
        sync_page.querySelector("#foo").innerText()
        == sync_page.querySelector("h1").innerText()
    )


def test_sync_click(sync_page):
    sync_page.setContent(
        """
    <button onclick="window.clicked=true">Bar</button>
    """
    )
    sync_page.click("text=Bar")
    assert sync_page.evaluate("()=>window.clicked")


def test_sync_nested_query_selector(sync_page):
    sync_page.setContent(
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
    e1 = sync_page.querySelector("#one")
    e2 = e1.querySelector(".two")
    e3 = e2.querySelector("label")
    assert e3.innerText() == "MyValue"


def test_sync_handle_multiple_pages(sync_context):
    page1 = sync_context.newPage()
    page2 = sync_context.newPage()
    assert len(sync_context.pages) == 2
    page1.setContent("one")
    page2.setContent("two")
    assert "one" in page1.content()
    assert "two" in page2.content()
    page1.close()
    assert len(sync_context.pages) == 1
    page2.close()
    assert len(sync_context.pages) == 0
    for page in [page1, page2]:
        with pytest.raises(Error):
            page.content()


def test_sync_wait_for_selector(sync_page):
    sync_page.evaluate(
        "() => setTimeout(() => document.write('<h1>foo</foo>'), 3 * 1000)"
    )
    sync_page.waitForSelector("h1", timeout=5000)


def test_sync_wait_for_selector_raise(sync_page):
    sync_page.evaluate(
        "() => setTimeout(() => document.write('<h1>foo</foo>'), 3 * 1000)"
    )
    with pytest.raises(Error) as exc:
        sync_page.waitForSelector("h1", timeout=2000)
    assert "Timeout 2000ms exceeded during" in exc.value.message


def test_sync_wait_for_event(sync_page):
    with sync_page.withWaitForEvent("popup", timeout=10000) as popup:
        sync_page.evaluate("() => window.open('https://example.com')")
        assert popup.value is None
    assert popup.value


def test_sync_wait_for_event_raise(sync_page):
    with pytest.raises(Error):
        with sync_page.withWaitForEvent("popup", timeout=500) as popup:
            assert False
        assert popup.value is None


def test_sync_make_existing_page_sync(page):
    page = SyncPage(page)
    assert page.evaluate("() => ({'playwright': true})") == {"playwright": True}
    page.setContent("<h1>myElement</h1>")
    page.waitForSelector("text=myElement")


def test_sync_network_events(sync_page, server):
    server.set_route(
        "/hello-world",
        lambda request: (
            request.setHeader("Content-Type", "text/plain"),
            request.write(b"Hello world"),
            request.finish(),
        ),
    )
    sync_page.goto(server.EMPTY_PAGE)
    messages = []
    sync_page.on(
        "request", lambda request: messages.append(f">>{request.method}{request.url}")
    )
    sync_page.on(
        "response",
        lambda response: messages.append(f"<<{response.status}{response.url}"),
    )
    response = sync_page.evaluate("""async ()=> (await fetch("/hello-world")).text()""")
    assert response == "Hello world"
    assert messages == [
        f">>GET{server.PREFIX}/hello-world",
        f"<<200{server.PREFIX}/hello-world",
    ]


def test_console_should_work(sync_page):
    messages = []
    sync_page.once("console", lambda m: messages.append(SyncConsoleMessage(m)))
    sync_page.evaluate('() => console.log("hello", 5, {foo: "bar"})'),
    assert len(messages) == 1
    message = messages[0]
    assert message.text == "hello 5 JSHandle@object"
    assert str(message) == "hello 5 JSHandle@object"
    assert message.type == "log"
    assert message.args[0].jsonValue() == "hello"
    assert message.args[1].jsonValue() == 5
    assert message.args[2].jsonValue() == {"foo": "bar"}


def test_sync_download(sync_browser, server):
    server.set_route(
        "/downloadWithFilename",
        lambda request: (
            request.setHeader("Content-Type", "application/octet-stream"),
            request.setHeader("Content-Disposition", "attachment; filename=file.txt"),
            request.write(b"Hello world"),
            request.finish(),
        ),
    )
    page = sync_browser.newPage(acceptDownloads=True)
    page.setContent(f'<a href="{server.PREFIX}/downloadWithFilename">download</a>')
    downloads = []

    page.on(
        "download", lambda download: downloads.append(SyncDownload(download)),
    )
    page.click("a")
    if len("download") == 0:
        page.waitForEvent("download")
    assert len(downloads) == 1
    download = downloads[0]
    assert download.suggestedFilename == "file.txt"
    path = download.path()
    assert os.path.isfile(path)
    with open(path, "r") as fd:
        assert fd.read() == "Hello world"
    page.close()


def test_sync_workers_page_workers(sync_page, server):
    workers = []
    sync_page.on(
        "worker", lambda worker: workers.append(SyncWorker(worker)),
    )
    sync_page.goto(server.PREFIX + "/worker/worker.html")
    sync_page.waitForEvent("worker")
    assert len(workers) == 1
    worker = sync_page.workers[0]
    assert "worker.js" in worker.url

    assert worker.evaluate('() => self["workerFunction"]()') == "worker function result"

    sync_page.goto(server.EMPTY_PAGE)
    assert len(sync_page.workers) == 0


# def test_dialog_should_work(page):
#     page = SyncPage(page)
#     dialog_events = []

#     def handle_dialog(dialog):
#         breakpoint()
#         dialog_events.append(dialog)
#         dialog.dismiss()

#     page.on(
#         "dialog", lambda dialog: handle_dialog(SyncDialog(dialog)),
#     )
#     page.setContent('<div onclick="window.alert(123)">Click me</div>')
#     print("ok1")
#     page.click("text=Click me")
#     print("nok")
#     assert len(dialog_events) == 1
#     breakpoint()
