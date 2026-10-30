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

"""Port of tests/library/browsercontext-har.spec.ts."""

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Awaitable, Callable

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import must


def echo_body(request: TestServerRequest) -> None:
    request.write(request.post_body or b"")
    request.finish()


async def test_HA_068_should_context_route_from_har_matching_the_method_and_following_redirects(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(path)
    page = await context.new_page()
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_HA_069_should_page_route_from_har_matching_the_method_and_following_redirects(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    page = await context.new_page()
    await page.route_from_har(path)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_HA_070_fallback_continue_should_continue_when_not_found_in_har(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(path, not_found="fallback")
    page = await context.new_page()
    await page.goto(server.PREFIX + "/one-style.html")
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_071_by_default_should_abort_requests_not_found_in_har(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(path)
    page = await context.new_page()
    with pytest.raises(Error):
        await page.goto(server.EMPTY_PAGE)


async def test_HA_072_fallback_continue_should_continue_requests_on_bad_har(
    context: BrowserContext, server: Server, tmp_path: Path
) -> None:
    path = tmp_path / "test.har"
    path.write_text(json.dumps({"log": {}}), encoding="utf-8")
    await context.route_from_har(path, not_found="fallback")
    page = await context.new_page()
    await page.goto(server.PREFIX + "/one-style.html")
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def fulfill_no_playwright(route: Route) -> None:
    assert route.request.url == "http://no.playwright/"
    await route.fulfill(
        status=200,
        content_type="text/html",
        body='<script src="./script.js"></script><div>hello</div>',
    )


async def test_HA_073_should_only_handle_requests_matching_url_filter(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(path, not_found="fallback", url="**/*.js")
    page = await context.new_page()
    await context.route("http://no.playwright/", fulfill_no_playwright)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )


async def test_HA_074_should_only_context_route_from_har_requests_matching_url_filter(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(path, url="**/*.js")
    page = await context.new_page()
    await context.route("http://no.playwright/", fulfill_no_playwright)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )


async def test_HA_075_should_only_page_route_from_har_requests_matching_url_filter(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    page = await context.new_page()
    await page.route_from_har(path, url="**/*.js")
    await context.route("http://no.playwright/", fulfill_no_playwright)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )


async def test_HA_076_should_apply_overrides_before_routing_from_har(
    context: BrowserContext, assetdir: Path
) -> None:
    # https://github.com/microsoft/playwright/issues/29190
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(path, url="**/*.js")
    page = await context.new_page()

    async def redirect_script(route: Route) -> None:
        await route.fallback(url="http://no.playwright/script2.js")

    async def fulfill_page(route: Route) -> None:
        await route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="http://no.playwright/my-script.js"></script><div>hello</div>',
        )

    await context.route("http://no.playwright/my-script.js", redirect_script)
    await context.route("http://test.example/", fulfill_page)
    await page.goto("http://test.example/")
    # HAR contains script2.js that sets the value.
    assert await page.evaluate("window.value") == "foo"


async def test_HA_077_should_support_regex_filter(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    await context.route_from_har(
        path, url=re.compile(r".*(\.js|.*\.css|no.playwright\/)$")
    )
    page = await context.new_page()
    await page.goto("http://no.playwright/")
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_HA_078_new_page_should_fulfill_from_har_matching_the_method_and_following_redirects(
    browser: Browser, assetdir: Path
) -> None:
    path = assetdir / "har-fulfill.har"
    page = await browser.new_page()
    await page.route_from_har(path)
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")
    await page.close()


async def test_HA_079_should_change_document_url_after_redirected_navigation(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-redirect.har"
    await context.route_from_har(path)
    page = await context.new_page()
    async with page.expect_navigation() as navigation_info:
        await page.goto("https://theverge.com/")
    await page.wait_for_url("https://www.theverge.com/")
    response = await navigation_info.value
    await expect(page).to_have_url("https://www.theverge.com/")
    assert must(response).request.url == "https://www.theverge.com/"
    assert await page.evaluate("() => location.href") == "https://www.theverge.com/"


async def test_HA_080_should_change_document_url_after_redirected_navigation_on_click(
    server: Server, context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-redirect.har"
    await context.route_from_har(path, url=re.compile(r".*theverge.*"))
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="https://theverge.com/">click me</a>')
    async with page.expect_navigation() as navigation_info:
        await page.click("text=click me")
    response = await navigation_info.value
    await expect(page).to_have_url("https://www.theverge.com/")
    assert must(response).request.url == "https://www.theverge.com/"
    assert await page.evaluate("() => location.href") == "https://www.theverge.com/"


async def test_HA_081_should_go_back_to_redirected_navigation(
    context: BrowserContext, assetdir: Path, server: Server
) -> None:
    path = assetdir / "har-redirect.har"
    await context.route_from_har(path, url=re.compile(r".*theverge.*"))
    page = await context.new_page()
    await page.goto("https://theverge.com/")
    await page.goto(server.EMPTY_PAGE)
    await expect(page).to_have_url(server.EMPTY_PAGE)
    response = await page.go_back()
    await expect(page).to_have_url("https://www.theverge.com/")
    assert must(response).request.url == "https://www.theverge.com/"
    assert await page.evaluate("() => location.href") == "https://www.theverge.com/"


async def test_HA_082_should_go_forward_to_redirected_navigation(
    context: BrowserContext, assetdir: Path, server: Server
) -> None:
    path = assetdir / "har-redirect.har"
    await context.route_from_har(path, url=re.compile(r".*theverge.*"))
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await expect(page).to_have_url(server.EMPTY_PAGE)
    await page.goto("https://theverge.com/")
    await expect(page).to_have_url("https://www.theverge.com/")
    await page.go_back()
    await expect(page).to_have_url(server.EMPTY_PAGE)
    response = await page.go_forward()
    await expect(page).to_have_url("https://www.theverge.com/")
    assert must(response).request.url == "https://www.theverge.com/"
    assert await page.evaluate("() => location.href") == "https://www.theverge.com/"


async def test_HA_083_should_reload_redirected_navigation(
    context: BrowserContext, assetdir: Path, server: Server
) -> None:
    path = assetdir / "har-redirect.har"
    await context.route_from_har(path, url=re.compile(r".*theverge.*"))
    page = await context.new_page()
    await page.goto("https://theverge.com/")
    await expect(page).to_have_url("https://www.theverge.com/")
    response = await page.reload()
    await expect(page).to_have_url("https://www.theverge.com/")
    assert must(response).request.url == "https://www.theverge.com/"
    assert await page.evaluate("() => location.href") == "https://www.theverge.com/"


async def test_HA_084_should_fulfill_from_har_with_content_in_a_file(
    context: BrowserContext, assetdir: Path
) -> None:
    path = assetdir / "har-sha1.har"
    await context.route_from_har(path)
    page = await context.new_page()
    await page.goto("http://no.playwright/")
    assert await page.content() == "<html><head></head><body>Hello, world</body></html>"


async def test_HA_085_should_round_trip_har_zip(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.ZIP"
    context1 = await context_factory(
        record_har_mode="minimal", record_har_path=har_path
    )
    page1 = await context1.new_page()
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    har_dir = tmp_path / "har"
    with zipfile.ZipFile(har_path) as zip_file:
        zip_file.extractall(har_dir)
    log = json.loads((har_dir / "har.har").read_text(encoding="utf-8"))["log"]
    assert isinstance(log["entries"][0]["response"]["content"]["_file"], str)

    context2 = await context_factory()
    await context2.route_from_har(har_path, not_found="abort")
    page2 = await context2.new_page()
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )

    # Python: zipfile builds the in-memory archive instead of yazl's output stream.
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zip_file:
        for entry in har_dir.iterdir():
            zip_file.write(
                entry, "Recording.HAR" if entry.name == "har.har" else entry.name
            )
    uppercase_har_path = tmp_path / "uppercase.har.zip"
    uppercase_har_path.write_bytes(output.getvalue())

    await context2.unroute_all(behavior="wait")
    await context2.route_from_har(uppercase_har_path, not_found="abort")
    await page2.reload()
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_114_should_reject_a_malformed_har_zip(
    context_factory: Callable[..., Awaitable[BrowserContext]], tmp_path: Path
) -> None:
    # Python: zipfile builds the in-memory archive instead of yazl's output stream.
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zip_file:
        zip_file.writestr("aa/x.har", b"{}")
    # yauzl reports '..' in an entry name as an 'error' event while reading entries.
    zip_data = output.getvalue().replace(b"aa/x.har", b"../x.har")
    har_path = tmp_path / "malformed.har.zip"
    har_path.write_bytes(zip_data)

    context = await context_factory()
    with pytest.raises(Error) as exc_info:
        await context.route_from_har(har_path)
    assert "invalid relative path: ../x.har" in exc_info.value.message


async def test_HA_086_should_produce_extracted_zip(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.har"
    context1 = await context_factory(
        record_har_mode="minimal", record_har_path=har_path, record_har_content="attach"
    )
    page1 = await context1.new_page()
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    assert har_path.exists()
    har = har_path.read_text(encoding="utf-8")
    assert "background-color" not in har

    context2 = await context_factory()
    await context2.route_from_har(har_path, not_found="abort")
    page2 = await context2.new_page()
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_087_should_round_trip_extracted_har_zip(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.zip"
    context1 = await context_factory(
        record_har_mode="minimal", record_har_path=har_path
    )
    page1 = await context1.new_page()
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    har_dir = tmp_path / "hardir"
    with zipfile.ZipFile(har_path) as zip_file:
        zip_file.extractall(har_dir)

    context2 = await context_factory()
    await context2.route_from_har(har_dir / "har.har")
    page2 = await context2.new_page()
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_088_should_round_trip_har_with_post_data(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    server.set_route("/echo", echo_body)

    har_path = tmp_path / "har.zip"
    context1 = await context_factory(
        record_har_mode="minimal", record_har_path=har_path
    )
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    fetch_function = """async (body) => {
        const response = await fetch('/echo', { method: 'POST', body });
        return await response.text();
    }"""

    assert await page1.evaluate(fetch_function, "1") == "1"
    assert await page1.evaluate(fetch_function, "2") == "2"
    assert await page1.evaluate(fetch_function, "3") == "3"
    await context1.close()

    server.reset()
    context2 = await context_factory()
    await context2.route_from_har(har_path)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await page2.evaluate(fetch_function, "1") == "1"
    assert await page2.evaluate(fetch_function, "2") == "2"
    assert await page2.evaluate(fetch_function, "3") == "3"
    result: Any
    try:
        result = await page2.evaluate(fetch_function, "4")
    except Error as error:
        result = error
    assert result


async def test_HA_089_should_record_overridden_requests_to_har(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/29190
    server.set_route("/echo", echo_body)

    har_path = tmp_path / "har.zip"
    context1 = await context_factory(
        record_har_mode="minimal", record_har_path=har_path
    )
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    fetch_function = """async (arg) => {
        const response = await fetch(arg.path, { method: 'POST', body: arg.body });
        return await response.text();
    }"""

    async def handle(route: Route) -> None:
        await route.fallback(
            url=server.PREFIX + "/echo",
            post_data=int(must(route.request.post_data)) + 10,
        )

    await page1.route("**/echo_redir", handle)
    assert (
        await page1.evaluate(fetch_function, {"path": "/echo_redir", "body": "1"})
        == "11"
    )
    assert (
        await page1.evaluate(fetch_function, {"path": "/echo_redir", "body": "2"})
        == "12"
    )
    await context1.close()

    server.reset()
    context2 = await context_factory()
    await context2.route_from_har(har_path)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await page2.evaluate(fetch_function, {"path": "/echo", "body": "11"}) == "11"
    assert await page2.evaluate(fetch_function, {"path": "/echo", "body": "12"}) == "12"


async def test_HA_090_should_disambiguate_by_header(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    def echo_baz(request: TestServerRequest) -> None:
        request.write((request.getHeader("baz") or "").encode())
        request.finish()

    server.set_route("/echo", echo_baz)

    har_path = tmp_path / "har.zip"
    context1 = await context_factory(
        record_har_mode="minimal", record_har_path=har_path
    )
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)

    fetch_function = """async (bazValue) => {
        const response = await fetch('/echo', {
            method: 'POST',
            body: '',
            headers: {
                foo: 'foo-value',
                bar: 'bar-value',
                baz: bazValue,
            }
        });
        return await response.text();
    }"""

    assert await page1.evaluate(fetch_function, "baz1") == "baz1"
    assert await page1.evaluate(fetch_function, "baz2") == "baz2"
    assert await page1.evaluate(fetch_function, "baz3") == "baz3"
    await context1.close()

    context2 = await context_factory()
    await context2.route_from_har(har_path)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    assert await page2.evaluate(fetch_function, "baz1") == "baz1"
    assert await page2.evaluate(fetch_function, "baz2") == "baz2"
    assert await page2.evaluate(fetch_function, "baz3") == "baz3"
    assert await page2.evaluate(fetch_function, "baz4") == "baz1"


async def test_HA_091_should_update_har_zip_for_context(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.zip"
    context1 = await context_factory()
    await context1.route_from_har(har_path, update=True)
    page1 = await context1.new_page()
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    context2 = await context_factory()
    await context2.route_from_har(har_path, not_found="abort")
    page2 = await context2.new_page()
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_092_should_ignore_boundary_when_matching_multipart_form_data_body(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/31495
    def handle_empty(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""
      <form id="form" action="form.html" enctype="multipart/form-data" method="POST">
      <input id="file" type="file" multiple />
      <button type="submit">Upload</button>
      </form>"""
        )
        request.finish()

    def handle_form(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(b"<div>done</div>")
        request.finish()

    server.set_route("/empty.html", handle_empty)
    server.set_route("/form.html", handle_form)

    har_path = tmp_path / "har.zip"
    context1 = await context_factory()
    await context1.route_from_har(har_path, update=True)
    page1 = await context1.new_page()
    await page1.goto(server.PREFIX + "/empty.html")
    with server.expect_request("/form.html") as request_info:
        await page1.locator("button").click()
        await expect(page1.locator("div")).to_have_text("done")
    req = request_info.value
    assert b"---" in must(req.post_body)
    await context1.close()

    context2 = await context_factory()
    await context2.route_from_har(har_path, not_found="abort")
    page2 = await context2.new_page()
    await page2.goto(server.PREFIX + "/empty.html")
    async with page2.expect_request(re.compile(r".*form.html")) as request_promise:
        await page2.locator("button").click()
    request = await request_promise.value
    assert await request.response()
    assert request.failure is None
    await expect(page2.locator("div")).to_have_text("done")


async def test_HA_093_should_record_single_set_cookie_headers(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/31495
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.responseHeaders.setRawHeaders("set-cookie", ["first=foo"])
        request.finish()

    server.set_route("/empty.html", handle)

    har_path = tmp_path / "har.zip"
    context1 = await context_factory()
    await context1.route_from_har(har_path, update=True)
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    cookie1 = await page1.evaluate("() => document.cookie")
    assert cookie1 == "first=foo"
    await context1.close()

    context2 = await context_factory()
    await context2.route_from_har(har_path, not_found="abort")
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    cookie2 = await page2.evaluate("() => document.cookie")
    assert cookie2 == "first=foo"


async def test_HA_094_should_record_multiple_set_cookie_headers(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/31495
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.responseHeaders.setRawHeaders("set-cookie", ["first=foo", "second=bar"])
        request.finish()

    server.set_route("/empty.html", handle)

    har_path = tmp_path / "har.zip"
    context1 = await context_factory()
    await context1.route_from_har(har_path, update=True)
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    cookie1 = await page1.evaluate("() => document.cookie")
    assert "; ".join(sorted(cookie1.split("; "))) == "first=foo; second=bar"
    await context1.close()

    context2 = await context_factory()
    await context2.route_from_har(har_path, not_found="abort")
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    cookie2 = await page2.evaluate("() => document.cookie")
    assert "; ".join(sorted(cookie2.split("; "))) == "first=foo; second=bar"


async def test_HA_095_should_update_har_zip_for_page(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.zip"
    context1 = await context_factory()
    page1 = await context1.new_page()
    await page1.route_from_har(har_path, update=True)
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    context2 = await context_factory()
    page2 = await context2.new_page()
    await page2.route_from_har(har_path, not_found="abort")
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_096_should_update_har_zip_for_page_with_different_options(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.zip"
    context1 = await context_factory()
    page1 = await context1.new_page()
    await page1.route_from_har(
        har_path, update=True, update_content="embed", update_mode="full"
    )
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    context2 = await context_factory()
    page2 = await context2.new_page()
    await page2.route_from_har(har_path, not_found="abort")
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_097_should_update_extracted_har_zip_for_page(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "har.har"
    context1 = await context_factory()
    page1 = await context1.new_page()
    await page1.route_from_har(har_path, update=True)
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    context2 = await context_factory()
    page2 = await context2.new_page()
    await page2.route_from_har(har_path, not_found="abort")
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_HA_098_page_unroute_all_should_stop_page_route_from_har(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    assetdir: Path,
) -> None:
    har_path = assetdir / "har-fulfill.har"
    context1 = await context_factory()
    page1 = await context1.new_page()
    # The har file contains requests for another domain, so the router
    # is expected to abort all requests.
    await page1.route_from_har(har_path, not_found="abort")
    with pytest.raises(Error):
        await page1.goto(server.EMPTY_PAGE)
    await page1.unroute_all(behavior="wait")
    response = await page1.goto(server.EMPTY_PAGE)
    assert must(response).ok


async def test_HA_099_context_unroute_all_should_stop_context_route_from_har(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    assetdir: Path,
) -> None:
    har_path = assetdir / "har-fulfill.har"
    context1 = await context_factory()
    page1 = await context1.new_page()
    # The har file contains requests for another domain, so the router
    # is expected to abort all requests.
    await context1.route_from_har(har_path, not_found="abort")
    with pytest.raises(Error):
        await page1.goto(server.EMPTY_PAGE)
    await context1.unroute_all(behavior="wait")
    response = await page1.goto(server.EMPTY_PAGE)
    assert must(response).ok


async def test_HA_100_should_ignore_aborted_requests(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/29311
    path = tmp_path / "test.har"
    server.set_route("/x", lambda request: request.loseConnection())
    context1 = await context_factory()
    await context1.route_from_har(path, update=True)
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    with server.expect_request("/x") as request_info:
        req = await page1.evaluate(
            "url => fetch(url).catch(e => 'cancelled')", server.PREFIX + "/x"
        )
    assert request_info.value
    assert req == "cancelled"
    await context1.close()

    server.reset()

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/plain")
        request.write(b"test")
        request.finish()

    server.set_route("/x", handle)
    context2 = await context_factory()
    await context2.route_from_har(path)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    # Start the fetch, wait for 1s, then check whether the fetch has settled: this
    # races the fetch against the timeout, like Promise.race() upstream.
    eval_promise = await page2.evaluate_handle(
        "url => ({ promise: fetch(url).catch(e => 'cancelled') })",
        server.PREFIX + "/x",
    )
    await page2.wait_for_timeout(1000)
    result = await eval_promise.evaluate(
        "holder => Promise.race([holder.promise, 'timeout'])"
    )
    assert result == "timeout"
