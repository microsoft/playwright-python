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

"""Port of tests/page/page-history.spec.ts."""

import contextlib
import json
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest

from playwright.sync_api import Error, Page, Request, Response, expect
from tests.server import Server, TestServerRequest, reactor
from tests.utils import must


def wait_until(page: Page, predicate: Callable[[], bool]) -> None:
    """Lets the event loop run until the predicate holds. The sync port of awaiting
    a server-side event, such as server.waitForRequest()."""
    while not predicate():
        page.wait_for_timeout(10)


def end(request: TestServerRequest, body: bytes) -> None:
    """Ends a held response from the test thread, like res.end(body)."""

    def finish() -> None:
        request.write(body)
        request.finish()

    reactor.callFromThread(finish)


def serve_html(body: Callable[[], str]) -> Callable[[TestServerRequest], None]:
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("content-type", "text/html; charset=utf-8")
        request.write(body().encode())
        request.finish()

    return handle


def test_NA_071_page_go_back_should_work_smoke(page: Page, server: Server) -> None:
    assert page.go_back() is None

    page.goto(server.EMPTY_PAGE)
    page.goto(server.PREFIX + "/grid.html")

    response = must(page.go_back())
    assert response.ok is True
    assert server.EMPTY_PAGE in response.url

    response = must(page.go_forward())
    assert response.ok is True
    assert "/grid.html" in response.url

    assert page.go_forward() is None


def test_NA_072_page_go_back_should_work_with_history_api(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
        """() => {
        history.pushState({}, '', '/first.html');
        history.pushState({}, '', '/second.html');
    }"""
    )
    assert page.url == server.PREFIX + "/second.html"

    page.go_back()
    assert page.url == server.PREFIX + "/first.html"
    page.go_back()
    assert page.url == server.EMPTY_PAGE
    page.go_forward()
    assert page.url == server.PREFIX + "/first.html"


def test_NA_073_page_go_back_should_work_for_file_urls(
    page: Page, server: Server, assetdir: Path, browser_channel: Optional[str]
) -> None:
    if browser_channel == "webkit-wsl":
        pytest.skip("webkit-wsl")

    url1 = (assetdir / "consolelog.html").as_uri()
    url2 = server.PREFIX + "/consolelog.html"
    with page.expect_event("console", lambda message: message.text == "here:" + url1):
        page.goto(url1)
    page.set_content(f"<a href='{url2}'>url2</a>")
    assert page.url.lower() == url1.lower()

    with page.expect_event("console", lambda message: message.text == "here:" + url2):
        page.click("a")
    assert page.url == url2

    with page.expect_event("console", lambda message: message.text == "here:" + url1):
        page.go_back()
    assert page.url.lower() == url1.lower()
    # Should be able to evaluate in the new context, and
    # not reach for the old cross-process one.
    assert page.evaluate("() => window.scrollX") == 0
    # Should be able to screenshot.
    page.screenshot()

    with page.expect_event("console", lambda message: message.text == "here:" + url2):
        page.go_forward()
    assert page.url == url2
    assert page.evaluate("() => window.scrollX") == 0
    page.screenshot()


def test_NA_074_go_back_go_forward_should_work_with_bfcache_able_pages(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/cached/bfcached.html")
    page.set_content(
        f"<a href={json.dumps(server.PREFIX + '/cached/bfcached.html?foo')}>click me</a>"
    )
    page.click("a")

    response = must(page.go_back())
    assert response.url == server.PREFIX + "/cached/bfcached.html"
    # BFCache should be disabled.
    assert page.evaluate("window.didShow") == {"persisted": False}

    response = must(page.go_forward())
    assert response.url == server.PREFIX + "/cached/bfcached.html?foo"


def test_NA_075_page_reload_should_work(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => window['_foo'] = 10")
    page.reload()
    assert page.evaluate("() => window['_foo']") is None


def test_NA_076_page_reload_should_work_with_data_url(
    page: Page, server: Server
) -> None:
    page.goto("data:text/html,hello")
    assert "hello" in page.content()
    assert page.reload() is None
    assert "hello" in page.content()


def navigate_during_form_submit(
    page: Page,
    server: Server,
    navigate: Callable[[], Optional[Response]],
) -> None:
    """The common part of the tests that navigate while a form submit is pending."""
    page.set_content(
        "<form method='POST' action='/post'>Form is here<input type='submit'></form>"
    )
    server.set_route("/post", lambda request: None)

    reload_failed: List[bool] = []

    def on_request(_: Request) -> None:
        with contextlib.suppress(Error):
            navigate()
        reload_failed.append(True)

    page.once("request", on_request)

    with contextlib.suppress(Error):
        page.click("input[type=submit]")
    wait_until(page, lambda: len(reload_failed) > 0)


def test_NA_077_page_reload_during_renderer_initiated_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/one-style.html")
    navigate_during_form_submit(page, server, page.reload)

    # Form submit should be canceled, and reload should eventually arrive
    # to the original one-style.html.
    page.wait_for_selector("text=hello")


def test_NA_078_page_reload_should_not_resolve_with_same_document_navigation(
    page: Page, server: Server, sync_gather: Callable[..., List[Any]]
) -> None:
    page.goto(server.EMPTY_PAGE)
    # 1. Make sure execution contexts are ready for fast evaluate.
    page.evaluate("1")

    # 2. Stall the reload request.
    responses: List[TestServerRequest] = []
    server.set_route("/empty.html", responses.append)

    def push_state() -> None:
        with contextlib.suppress(Error):
            page.evaluate("() => { window.history.pushState({}, ''); }")

    def serve() -> None:
        # 5. Serve the request, it should resolve the reload.
        wait_until(page, lambda: len(responses) > 0)
        end(responses[0], b"hello")

    [_, reload_response, _, _] = sync_gather(
        # 3. Trigger push state that could resolve the reload.
        lambda: push_state(),
        # 4. Trigger the reload, it should not resolve.
        lambda: page.reload(),
        # 5. Trigger push state again, for the good measure :)
        lambda: push_state(),
        serve,
    )

    # 6. Check the reload response.
    got_response = must(reload_response)
    assert got_response.text() == "hello"


def test_NA_079_page_reload_should_work_with_same_origin_redirect(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_redirect("/empty.html", server.PREFIX + "/title.html")
    page.reload()
    expect(page).to_have_url(server.PREFIX + "/title.html")


def test_NA_080_page_reload_should_work_with_cross_origin_redirect(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_redirect("/empty.html", server.CROSS_PROCESS_PREFIX + "/title.html")
    page.reload()
    expect(page).to_have_url(server.CROSS_PROCESS_PREFIX + "/title.html")


def test_NA_081_page_reload_should_work_on_a_page_with_a_hash(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE + "#hash")
    page.reload()
    expect(page).to_have_url(server.EMPTY_PAGE + "#hash")


def test_NA_082_page_reload_should_work_on_a_page_with_a_hash_at_the_end(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE + "#")
    page.reload()
    expect(page).to_have_url(server.EMPTY_PAGE + "#")


def test_NA_083_page_go_back_during_renderer_initiated_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.PREFIX + "/one-style.html")
    page.goto(server.EMPTY_PAGE)
    navigate_during_form_submit(page, server, page.go_back)

    # Form submit should be canceled, and goBack should eventually arrive
    # to the original one-style.html.
    page.wait_for_selector("text=hello")


def test_NA_084_page_go_forward_during_renderer_initiated_navigation(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.goto(server.PREFIX + "/one-style.html")
    page.go_back()

    navigate_during_form_submit(page, server, page.go_forward)

    # Form submit should be canceled, and goForward should eventually arrive
    # to the original one-style.html.
    page.wait_for_selector("text=hello")


def poll_until_equal(page: Page, get: Callable[[], Any], expected: Any) -> None:
    """Port of expect.poll(get).toEqual(expected) with the default 5s timeout."""
    for _ in range(50):
        if get() == expected:
            break
        page.wait_for_timeout(100)
    assert get() == expected


def test_NA_085_regression_test_for_issue_20791(page: Page, server: Server) -> None:
    # iframe access parent frame to log a value from it.
    server.set_route(
        "/iframe.html",
        serve_html(
            lambda: """
      <!doctype html>
      <script type="text/javascript">
        console.log(window.parent.foo);
      </script>
    """
        ),
    )
    server.set_route(
        "/main.html",
        serve_html(
            lambda: f"""
      <!doctype html>
      <iframe id=myframe src="about:blank"></iframe>
      <script type="text/javascript">
        setTimeout(() => window.foo = 'foo', 0);
        setTimeout(() => myframe.contentDocument.location.href = '{server.PREFIX}/iframe.html', 0);
      </script>
    """
        ),
    )
    messages: List[str] = []
    page.on("console", lambda msg: messages.append(msg.text))
    page.goto(server.PREFIX + "/main.html")
    poll_until_equal(page, lambda: messages, ["foo"])
    page.reload()
    poll_until_equal(page, lambda: messages, ["foo", "foo"])


def test_NA_086_should_reload_proper_page(page: Page, server: Server) -> None:
    main_request: List[int] = []
    popup_request: List[int] = []

    def main_body() -> str:
        main_request.append(1)
        return f"<!doctype html><h1>main: {len(main_request)}</h1>"

    def popup_body() -> str:
        popup_request.append(1)
        return f"<!doctype html><h1>popup: {len(popup_request)}</h1>"

    server.set_route("/main.html", serve_html(main_body))
    server.set_route("/popup.html", serve_html(popup_body))
    page.goto(server.PREFIX + "/main.html")
    with page.expect_popup() as popup_info:
        page.evaluate("() => window.open('/popup.html')")
    popup = popup_info.value
    expect(page.locator("h1")).to_have_text("main: 1")
    expect(popup.locator("h1")).to_have_text("popup: 1")

    page.reload()
    expect(page.locator("h1")).to_have_text("main: 2")
    expect(popup.locator("h1")).to_have_text("popup: 1")

    popup.reload()
    expect(page.locator("h1")).to_have_text("main: 2")
    expect(popup.locator("h1")).to_have_text("popup: 2")
