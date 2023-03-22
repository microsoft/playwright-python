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

import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

from playwright.sync_api import Browser, BrowserContext, Error, Page, Route, expect
from tests.server import Server


def test_should_work(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path)
    page = context.new_page()
    page.goto(server.EMPTY_PAGE)
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data


def test_should_omit_content(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path, record_har_content="omit")
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert "text" not in content1
        assert "encoding" not in content1


def test_should_omit_content_legacy(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path, record_har_omit_content=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert "text" not in content1
        assert "encoding" not in content1


def test_should_attach_content(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har.zip")
    context = browser.new_context(
        record_har_path=path,
        record_har_content="attach",
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    context.close()
    with zipfile.ZipFile(path) as z:
        with z.open("har.har") as har:
            entries = json.load(har)["log"]["entries"]

            assert "encoding" not in entries[0]["response"]["content"]
            assert (
                entries[0]["response"]["content"]["mimeType"]
                == "text/html; charset=utf-8"
            )
            assert (
                "75841480e2606c03389077304342fac2c58ccb1b"
                in entries[0]["response"]["content"]["_file"]
            )
            assert entries[0]["response"]["content"]["size"] >= 96
            assert entries[0]["response"]["content"]["compression"] == 0

            assert "encoding" not in entries[1]["response"]["content"]
            assert (
                entries[1]["response"]["content"]["mimeType"]
                == "text/css; charset=utf-8"
            )
            assert (
                "79f739d7bc88e80f55b9891a22bf13a2b4e18adb"
                in entries[1]["response"]["content"]["_file"]
            )
            assert entries[1]["response"]["content"]["size"] >= 37
            assert entries[1]["response"]["content"]["compression"] == 0

            assert "encoding" not in entries[2]["response"]["content"]
            assert entries[2]["response"]["content"]["mimeType"] == "image/png"
            assert (
                "a4c3a18f0bb83f5d9fe7ce561e065c36205762fa"
                in entries[2]["response"]["content"]["_file"]
            )
            assert entries[2]["response"]["content"]["size"] >= 6000
            assert entries[2]["response"]["content"]["compression"] == 0

            with z.open("75841480e2606c03389077304342fac2c58ccb1b.html") as f:
                assert b"HAR Page" in f.read()

            with z.open("79f739d7bc88e80f55b9891a22bf13a2b4e18adb.css") as f:
                assert b"pink" in f.read()

            with z.open("a4c3a18f0bb83f5d9fe7ce561e065c36205762fa.png") as f:
                assert len(f.read()) == entries[2]["response"]["content"]["size"]


def test_should_include_content(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(record_har_path=path)
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert content1["mimeType"] == "text/html; charset=utf-8"
        assert "HAR Page" in content1["text"]


def test_should_default_to_full_mode(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        record_har_path=path,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] >= 0


def test_should_support_minimal_mode(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        record_har_path=path,
        record_har_mode="minimal",
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] == -1


def test_should_filter_by_glob(browser: Browser, server: Server, tmpdir: str) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter="/*.css",
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("one-style.css")


def test_should_filter_by_regexp(browser: Browser, server: Server, tmpdir: str) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter=re.compile("HAR.X?HTML", re.I),
        ignore_https_errors=True,
    )
    page = context.new_page()
    page.goto(server.PREFIX + "/har.html")
    context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("har.html")


def test_should_context_route_from_har_matching_the_method_and_following_redirects(
    context: BrowserContext, assetdir: Path
) -> None:
    context.route_from_har(har=assetdir / "har-fulfill.har")
    page = context.new_page()
    page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


def test_should_page_route_from_har_matching_the_method_and_following_redirects(
    page: Page, assetdir: Path
) -> None:
    page.route_from_har(har=assetdir / "har-fulfill.har")
    page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


def test_fallback_continue_should_continue_when_not_found_in_har(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(har=assetdir / "har-fulfill.har", not_found="fallback")
    page = context.new_page()
    page.goto(server.PREFIX + "/one-style.html")
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")


def test_by_default_should_abort_requests_not_found_in_har(
    context: BrowserContext,
    server: Server,
    assetdir: Path,
    is_chromium: bool,
    is_webkit: bool,
) -> None:
    context.route_from_har(har=assetdir / "har-fulfill.har")
    page = context.new_page()

    with pytest.raises(Error) as exc_info:
        page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    if is_chromium:
        assert "net::ERR_FAILED" in exc_info.value.message
    elif is_webkit:
        assert "Blocked by Web Inspector" in exc_info.value.message
    else:
        assert "NS_ERROR_FAILURE" in exc_info.value.message


def test_fallback_continue_should_continue_requests_on_bad_har(
    context: BrowserContext, server: Server, tmpdir: Path
) -> None:
    path_to_invalid_har = tmpdir / "invalid.har"
    with path_to_invalid_har.open("w") as f:
        json.dump({"log": {}}, f)
    context.route_from_har(har=path_to_invalid_har, not_found="fallback")
    page = context.new_page()
    page.goto(server.PREFIX + "/one-style.html")
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")


def test_should_only_handle_requests_matching_url_filter(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(
        har=assetdir / "har-fulfill.har", not_found="fallback", url="**/*.js"
    )
    page = context.new_page()

    def handler(route: Route) -> None:
        assert route.request.url == "http://no.playwright/"
        route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="./script.js"></script><div>hello</div>',
        )

    context.route("http://no.playwright/", handler)
    page.goto("http://no.playwright/")
    assert page.evaluate("window.value") == "foo"
    expect(page.locator("body")).to_have_css("background-color", "rgba(0, 0, 0, 0)")


def test_should_only_handle_requests_matching_url_filter_no_fallback(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(har=assetdir / "har-fulfill.har", url="**/*.js")
    page = context.new_page()

    def handler(route: Route) -> None:
        assert route.request.url == "http://no.playwright/"
        route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="./script.js"></script><div>hello</div>',
        )

    context.route("http://no.playwright/", handler)
    page.goto("http://no.playwright/")
    assert page.evaluate("window.value") == "foo"
    expect(page.locator("body")).to_have_css("background-color", "rgba(0, 0, 0, 0)")


def test_should_only_handle_requests_matching_url_filter_no_fallback_page(
    page: Page, server: Server, assetdir: Path
) -> None:
    page.route_from_har(har=assetdir / "har-fulfill.har", url="**/*.js")

    def handler(route: Route) -> None:
        assert route.request.url == "http://no.playwright/"
        route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="./script.js"></script><div>hello</div>',
        )

    page.route("http://no.playwright/", handler)
    page.goto("http://no.playwright/")
    assert page.evaluate("window.value") == "foo"
    expect(page.locator("body")).to_have_css("background-color", "rgba(0, 0, 0, 0)")


def test_should_support_regex_filter(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(
        har=assetdir / "har-fulfill.har",
        url=re.compile(r".*(\.js|.*\.css|no.playwright\/)"),
    )
    page = context.new_page()
    page.goto("http://no.playwright/")
    assert page.evaluate("window.value") == "foo"
    expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


def test_should_go_back_to_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = context.new_page()
    page.goto("https://theverge.com/")
    page.goto(server.EMPTY_PAGE)
    expect(page).to_have_url(server.EMPTY_PAGE)

    response = page.go_back()
    assert response
    expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert page.evaluate("window.location.href") == "https://www.theverge.com/"


@pytest.mark.skip_browser(
    "firefox"
)  # skipped upstream (https://github.com/microsoft/playwright/blob/6a8d835145e2f4002ee00b67a80a1f70af956703/tests/library/browsercontext-har.spec.ts#L214)
def test_should_go_forward_to_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = context.new_page()
    page.goto("https://theverge.com/")
    page.goto(server.EMPTY_PAGE)
    expect(page).to_have_url(server.EMPTY_PAGE)
    page.goto("https://theverge.com/")
    expect(page).to_have_url("https://www.theverge.com/")
    page.go_back()
    expect(page).to_have_url(server.EMPTY_PAGE)
    response = page.go_forward()
    assert response
    expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert page.evaluate("window.location.href") == "https://www.theverge.com/"


def test_should_reload_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = context.new_page()
    page.goto("https://theverge.com/")
    expect(page).to_have_url("https://www.theverge.com/")
    response = page.reload()
    assert response
    expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert page.evaluate("window.location.href") == "https://www.theverge.com/"


def test_should_fulfill_from_har_with_content_in_a_file(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    context.route_from_har(har=assetdir / "har-sha1.har")
    page = context.new_page()
    page.goto("http://no.playwright/")
    assert page.content() == "<html><head></head><body>Hello, world</body></html>"


def test_should_round_trip_har_zip(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context_1 = browser.new_context(record_har_mode="minimal", record_har_path=har_path)
    page_1 = context_1.new_page()
    page_1.goto(server.PREFIX + "/one-style.html")
    context_1.close()

    context_2 = browser.new_context()
    context_2.route_from_har(har=har_path, not_found="abort")
    page_2 = context_2.new_page()
    page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in page_2.content()
    expect(page_2.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")


def test_should_round_trip_har_with_post_data(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    server.set_route(
        "/echo", lambda req: (req.write(cast(Any, req).post_body), req.finish())
    )
    fetch_function = """
        async (body) => {
            const response = await fetch('/echo', { method: 'POST', body });
            return response.text();
        };
    """
    har_path = tmpdir / "har.zip"
    context_1 = browser.new_context(record_har_mode="minimal", record_har_path=har_path)
    page_1 = context_1.new_page()
    page_1.goto(server.EMPTY_PAGE)

    assert page_1.evaluate(fetch_function, "1") == "1"
    assert page_1.evaluate(fetch_function, "2") == "2"
    assert page_1.evaluate(fetch_function, "3") == "3"
    context_1.close()

    context_2 = browser.new_context()
    context_2.route_from_har(har=har_path, not_found="abort")
    page_2 = context_2.new_page()
    page_2.goto(server.EMPTY_PAGE)
    assert page_2.evaluate(fetch_function, "1") == "1"
    assert page_2.evaluate(fetch_function, "2") == "2"
    assert page_2.evaluate(fetch_function, "3") == "3"
    with pytest.raises(Exception):
        page_2.evaluate(fetch_function, "4")


def test_should_disambiguate_by_header(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    server.set_route(
        "/echo",
        lambda req: (req.write(cast(str, req.getHeader("baz")).encode()), req.finish()),
    )
    fetch_function = """
        async (bazValue) => {
            const response = await fetch('/echo', {
            method: 'POST',
            body: '',
            headers: {
                foo: 'foo-value',
                bar: 'bar-value',
                baz: bazValue,
            }
            });
            return response.text();
        };
    """
    har_path = tmpdir / "har.zip"
    context_1 = browser.new_context(record_har_mode="minimal", record_har_path=har_path)
    page_1 = context_1.new_page()
    page_1.goto(server.EMPTY_PAGE)

    assert page_1.evaluate(fetch_function, "baz1") == "baz1"
    assert page_1.evaluate(fetch_function, "baz2") == "baz2"
    assert page_1.evaluate(fetch_function, "baz3") == "baz3"
    context_1.close()

    context_2 = browser.new_context()
    context_2.route_from_har(har=har_path)
    page_2 = context_2.new_page()
    page_2.goto(server.EMPTY_PAGE)
    assert page_2.evaluate(fetch_function, "baz1") == "baz1"
    assert page_2.evaluate(fetch_function, "baz2") == "baz2"
    assert page_2.evaluate(fetch_function, "baz3") == "baz3"
    assert page_2.evaluate(fetch_function, "baz4") == "baz1"


def test_should_produce_extracted_zip(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.har"
    context = browser.new_context(
        record_har_mode="minimal", record_har_path=har_path, record_har_content="attach"
    )
    page_1 = context.new_page()
    page_1.goto(server.PREFIX + "/one-style.html")
    context.close()

    assert har_path.exists()
    with har_path.open() as r:
        content = r.read()
        assert "log" in content
        assert "background-color" not in r.read()

    context_2 = browser.new_context()
    context_2.route_from_har(har_path, not_found="abort")
    page_2 = context_2.new_page()
    page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in page_2.content()
    expect(page_2.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")


def test_should_update_har_zip_for_context(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context = browser.new_context()
    context.route_from_har(har_path, update=True)
    page_1 = context.new_page()
    page_1.goto(server.PREFIX + "/one-style.html")
    context.close()

    assert har_path.exists()

    context_2 = browser.new_context()
    context_2.route_from_har(har_path, not_found="abort")
    page_2 = context_2.new_page()
    page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in page_2.content()
    expect(page_2.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")


def test_should_update_har_zip_for_page(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context = browser.new_context()
    page_1 = context.new_page()
    page_1.route_from_har(har_path, update=True)
    page_1.goto(server.PREFIX + "/one-style.html")
    context.close()

    assert har_path.exists()

    context_2 = browser.new_context()
    page_2 = context_2.new_page()
    page_2.route_from_har(har_path, not_found="abort")
    page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in page_2.content()
    expect(page_2.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")


def test_should_update_har_zip_for_page_with_different_options(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context1 = browser.new_context()
    page1 = context1.new_page()
    page1.route_from_har(
        har_path, update=True, update_content="embed", update_mode="full"
    )
    page1.goto(server.PREFIX + "/one-style.html")
    context1.close()

    context2 = browser.new_context()
    page2 = context2.new_page()
    page2.route_from_har(har_path, not_found="abort")
    page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in page2.content()
    expect(page2.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")
    context2.close()


def test_should_update_extracted_har_zip_for_page(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.har"
    context = browser.new_context()
    page_1 = context.new_page()
    page_1.route_from_har(har_path, update=True)
    page_1.goto(server.PREFIX + "/one-style.html")
    context.close()

    assert har_path.exists()
    with har_path.open() as r:
        content = r.read()
        assert "log" in content
        assert "background-color" not in r.read()

    context_2 = browser.new_context()
    page_2 = context_2.new_page()
    page_2.route_from_har(har_path, not_found="abort")
    page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in page_2.content()
    expect(page_2.locator("body")).to_have_css("background-color", "rgb(255, 192, 203)")
