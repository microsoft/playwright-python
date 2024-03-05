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
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Awaitable, Callable, cast

import pytest

from playwright.async_api import Browser, BrowserContext, Error, Page, Route, expect
from tests.server import Server, TestServerRequest
from tests.utils import must


async def test_should_work(browser: Browser, server: Server, tmpdir: Path) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(record_har_path=path)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data


async def test_should_omit_content(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        record_har_path=path,
        record_har_content="omit",
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        content1 = log["entries"][0]["response"]["content"]
        assert "text" not in content1
        assert "encoding" not in content1


async def test_should_omit_content_legacy(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        record_har_path=path, record_har_omit_content=True
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        content1 = log["entries"][0]["response"]["content"]
        assert "text" not in content1
        assert "encoding" not in content1


async def test_should_attach_content(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har.zip")
    context = await browser.new_context(
        record_har_path=path,
        record_har_content="attach",
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    await context.close()
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


async def test_should_not_omit_content(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        record_har_path=path, record_har_omit_content=False
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        content1 = data["log"]["entries"][0]["response"]["content"]
        assert "text" in content1


async def test_should_include_content(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(record_har_path=path)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]

        content1 = log["entries"][0]["response"]["content"]
        assert content1["mimeType"] == "text/html; charset=utf-8"
        assert "HAR Page" in content1["text"]


async def test_should_default_to_full_mode(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        record_har_path=path,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] >= 0


async def test_should_support_minimal_mode(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        record_har_path=path,
        record_har_mode="minimal",
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert log["entries"][0]["request"]["bodySize"] == -1


async def test_should_filter_by_glob(
    browser: Browser, server: Server, tmpdir: str
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter="/*.css",
        ignore_https_errors=True,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("one-style.css")


async def test_should_filter_by_regexp(
    browser: Browser, server: Server, tmpdir: str
) -> None:
    path = os.path.join(tmpdir, "log.har")
    context = await browser.new_context(
        base_url=server.PREFIX,
        record_har_path=path,
        record_har_url_filter=re.compile("HAR.X?HTML", re.I),
        ignore_https_errors=True,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    with open(path) as f:
        data = json.load(f)
        assert "log" in data
        log = data["log"]
        assert len(log["entries"]) == 1
        assert log["entries"][0]["request"]["url"].endswith("har.html")


async def test_should_context_route_from_har_matching_the_method_and_following_redirects(
    context: BrowserContext, assetdir: Path
) -> None:
    await context.route_from_har(har=assetdir / "har-fulfill.har")
    page = await context.new_page()
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_should_page_route_from_har_matching_the_method_and_following_redirects(
    page: Page, assetdir: Path
) -> None:
    await page.route_from_har(har=assetdir / "har-fulfill.har")
    await page.goto("http://no.playwright/")
    # HAR contains a redirect for the script that should be followed automatically.
    assert await page.evaluate("window.value") == "foo"
    # HAR contains a POST for the css file that should not be used.
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_fallback_continue_should_continue_when_not_found_in_har(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(har=assetdir / "har-fulfill.har", not_found="fallback")
    page = await context.new_page()
    await page.goto(server.PREFIX + "/one-style.html")
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_by_default_should_abort_requests_not_found_in_har(
    context: BrowserContext,
    server: Server,
    assetdir: Path,
    is_chromium: bool,
    is_webkit: bool,
) -> None:
    await context.route_from_har(har=assetdir / "har-fulfill.har")
    page = await context.new_page()

    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    if is_chromium:
        assert "net::ERR_FAILED" in exc_info.value.message
    elif is_webkit:
        assert "Blocked by Web Inspector" in exc_info.value.message
    else:
        assert "NS_ERROR_FAILURE" in exc_info.value.message


async def test_fallback_continue_should_continue_requests_on_bad_har(
    context: BrowserContext, server: Server, tmpdir: Path
) -> None:
    path_to_invalid_har = tmpdir / "invalid.har"
    with path_to_invalid_har.open("w") as f:
        json.dump({"log": {}}, f)
    await context.route_from_har(har=path_to_invalid_har, not_found="fallback")
    page = await context.new_page()
    await page.goto(server.PREFIX + "/one-style.html")
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_should_only_handle_requests_matching_url_filter(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(
        har=assetdir / "har-fulfill.har", not_found="fallback", url="**/*.js"
    )
    page = await context.new_page()

    async def handler(route: Route) -> None:
        assert route.request.url == "http://no.playwright/"
        await route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="./script.js"></script><div>hello</div>',
        )

    await context.route("http://no.playwright/", handler)
    await page.goto("http://no.playwright/")
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )


async def test_should_only_handle_requests_matching_url_filter_no_fallback(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(har=assetdir / "har-fulfill.har", url="**/*.js")
    page = await context.new_page()

    async def handler(route: Route) -> None:
        assert route.request.url == "http://no.playwright/"
        await route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="./script.js"></script><div>hello</div>',
        )

    await context.route("http://no.playwright/", handler)
    await page.goto("http://no.playwright/")
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )


async def test_should_only_handle_requests_matching_url_filter_no_fallback_page(
    page: Page, server: Server, assetdir: Path
) -> None:
    await page.route_from_har(har=assetdir / "har-fulfill.har", url="**/*.js")

    async def handler(route: Route) -> None:
        assert route.request.url == "http://no.playwright/"
        await route.fulfill(
            status=200,
            content_type="text/html",
            body='<script src="./script.js"></script><div>hello</div>',
        )

    await page.route("http://no.playwright/", handler)
    await page.goto("http://no.playwright/")
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css(
        "background-color", "rgba(0, 0, 0, 0)"
    )


async def test_should_support_regex_filter(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(
        har=assetdir / "har-fulfill.har",
        url=re.compile(r".*(\.js|.*\.css|no.playwright\/)"),
    )
    page = await context.new_page()
    await page.goto("http://no.playwright/")
    assert await page.evaluate("window.value") == "foo"
    await expect(page.locator("body")).to_have_css("background-color", "rgb(255, 0, 0)")


async def test_should_change_document_url_after_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(har=assetdir / "har-redirect.har")
    page = await context.new_page()

    async with page.expect_navigation() as navigation_info:
        await asyncio.gather(
            page.wait_for_url("https://www.theverge.com/"),
            page.goto("https://theverge.com/"),
        )

    response = await navigation_info.value
    await expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert await page.evaluate("window.location.href") == "https://www.theverge.com/"


async def test_should_change_document_url_after_redirected_navigation_on_click(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="https://theverge.com/">click me</a>')
    async with page.expect_navigation() as navigation_info:
        await asyncio.gather(
            page.wait_for_url("https://www.theverge.com/"),
            page.click("text=click me"),
        )

    response = await navigation_info.value
    await expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert await page.evaluate("window.location.href") == "https://www.theverge.com/"


async def test_should_go_back_to_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = await context.new_page()
    await page.goto("https://theverge.com/")
    await page.goto(server.EMPTY_PAGE)
    await expect(page).to_have_url(server.EMPTY_PAGE)

    response = await page.go_back()
    assert response
    await expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert await page.evaluate("window.location.href") == "https://www.theverge.com/"


async def test_should_go_forward_to_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = await context.new_page()
    await page.goto("https://theverge.com/")
    await page.goto(server.EMPTY_PAGE)
    await expect(page).to_have_url(server.EMPTY_PAGE)
    await page.goto("https://theverge.com/")
    await expect(page).to_have_url("https://www.theverge.com/")
    await page.go_back()
    await expect(page).to_have_url(server.EMPTY_PAGE)
    response = await page.go_forward()
    assert response
    await expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert await page.evaluate("window.location.href") == "https://www.theverge.com/"


async def test_should_reload_redirected_navigation(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(
        har=assetdir / "har-redirect.har", url=re.compile(r"/.*theverge.*/")
    )
    page = await context.new_page()
    await page.goto("https://theverge.com/")
    await expect(page).to_have_url("https://www.theverge.com/")
    response = await page.reload()
    assert response
    await expect(page).to_have_url("https://www.theverge.com/")
    assert response.request.url == "https://www.theverge.com/"
    assert await page.evaluate("window.location.href") == "https://www.theverge.com/"


async def test_should_fulfill_from_har_with_content_in_a_file(
    context: BrowserContext, server: Server, assetdir: Path
) -> None:
    await context.route_from_har(har=assetdir / "har-sha1.har")
    page = await context.new_page()
    await page.goto("http://no.playwright/")
    assert await page.content() == "<html><head></head><body>Hello, world</body></html>"


async def test_should_round_trip_har_zip(
    browser: Browser, server: Server, assetdir: Path, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context_1 = await browser.new_context(
        record_har_mode="minimal", record_har_path=har_path
    )
    page_1 = await context_1.new_page()
    await page_1.goto(server.PREFIX + "/one-style.html")
    await context_1.close()

    context_2 = await browser.new_context()
    await context_2.route_from_har(har=har_path, not_found="abort")
    page_2 = await context_2.new_page()
    await page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page_2.content()
    await expect(page_2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_should_round_trip_har_with_post_data(
    browser: Browser, server: Server, assetdir: Path, tmpdir: Path
) -> None:
    server.set_route("/echo", lambda req: (req.write(req.post_body), req.finish()))
    fetch_function = """
        async (body) => {
            const response = await fetch('/echo', { method: 'POST', body });
            return await response.text();
        };
    """
    har_path = tmpdir / "har.zip"
    context_1 = await browser.new_context(
        record_har_mode="minimal", record_har_path=har_path
    )
    page_1 = await context_1.new_page()
    await page_1.goto(server.EMPTY_PAGE)

    assert await page_1.evaluate(fetch_function, "1") == "1"
    assert await page_1.evaluate(fetch_function, "2") == "2"
    assert await page_1.evaluate(fetch_function, "3") == "3"
    await context_1.close()

    context_2 = await browser.new_context()
    await context_2.route_from_har(har=har_path, not_found="abort")
    page_2 = await context_2.new_page()
    await page_2.goto(server.EMPTY_PAGE)
    assert await page_2.evaluate(fetch_function, "1") == "1"
    assert await page_2.evaluate(fetch_function, "2") == "2"
    assert await page_2.evaluate(fetch_function, "3") == "3"
    with pytest.raises(Exception):
        await page_2.evaluate(fetch_function, "4")


async def test_should_disambiguate_by_header(
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
            return await response.text();
        };
    """
    har_path = tmpdir / "har.zip"
    context_1 = await browser.new_context(
        record_har_mode="minimal", record_har_path=har_path
    )
    page_1 = await context_1.new_page()
    await page_1.goto(server.EMPTY_PAGE)

    assert await page_1.evaluate(fetch_function, "baz1") == "baz1"
    assert await page_1.evaluate(fetch_function, "baz2") == "baz2"
    assert await page_1.evaluate(fetch_function, "baz3") == "baz3"
    await context_1.close()

    context_2 = await browser.new_context()
    await context_2.route_from_har(har=har_path)
    page_2 = await context_2.new_page()
    await page_2.goto(server.EMPTY_PAGE)
    assert await page_2.evaluate(fetch_function, "baz1") == "baz1"
    assert await page_2.evaluate(fetch_function, "baz2") == "baz2"
    assert await page_2.evaluate(fetch_function, "baz3") == "baz3"
    assert await page_2.evaluate(fetch_function, "baz4") == "baz1"


async def test_should_produce_extracted_zip(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.har"
    context = await browser.new_context(
        record_har_mode="minimal", record_har_path=har_path, record_har_content="attach"
    )
    page_1 = await context.new_page()
    await page_1.goto(server.PREFIX + "/one-style.html")
    await context.close()

    assert har_path.exists()
    with har_path.open() as r:
        content = r.read()
        assert "log" in content
        assert "background-color" not in r.read()

    context_2 = await browser.new_context()
    await context_2.route_from_har(har_path, not_found="abort")
    page_2 = await context_2.new_page()
    await page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page_2.content()
    await expect(page_2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_should_update_har_zip_for_context(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context = await browser.new_context()
    await context.route_from_har(har_path, update=True)
    page_1 = await context.new_page()
    await page_1.goto(server.PREFIX + "/one-style.html")
    await context.close()

    assert har_path.exists()

    context_2 = await browser.new_context()
    await context_2.route_from_har(har_path, not_found="abort")
    page_2 = await context_2.new_page()
    await page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page_2.content()
    await expect(page_2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_page_unroute_all_should_stop_page_route_from_har(
    context_factory: Callable[[], Awaitable[BrowserContext]],
    server: Server,
    assetdir: Path,
) -> None:
    har_path = assetdir / "har-fulfill.har"
    context1 = await context_factory()
    page1 = await context1.new_page()
    # The har file contains requests for another domain, so the router
    # is expected to abort all requests.
    await page1.route_from_har(har_path, not_found="abort")
    with pytest.raises(Error) as exc_info:
        await page1.goto(server.EMPTY_PAGE)
    assert exc_info.value
    await page1.unroute_all(behavior="wait")
    response = must(await page1.goto(server.EMPTY_PAGE))
    assert response.ok


async def test_context_unroute_call_should_stop_context_route_from_har(
    context_factory: Callable[[], Awaitable[BrowserContext]],
    server: Server,
    assetdir: Path,
) -> None:
    har_path = assetdir / "har-fulfill.har"
    context1 = await context_factory()
    page1 = await context1.new_page()
    # The har file contains requests for another domain, so the router
    # is expected to abort all requests.
    await context1.route_from_har(har_path, not_found="abort")
    with pytest.raises(Error) as exc_info:
        await page1.goto(server.EMPTY_PAGE)
    assert exc_info.value
    await context1.unroute_all(behavior="wait")
    response = must(await page1.goto(server.EMPTY_PAGE))
    assert must(response).ok


async def test_should_update_har_zip_for_page(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context = await browser.new_context()
    page_1 = await context.new_page()
    await page_1.route_from_har(har_path, update=True)
    await page_1.goto(server.PREFIX + "/one-style.html")
    await context.close()

    assert har_path.exists()

    context_2 = await browser.new_context()
    page_2 = await context_2.new_page()
    await page_2.route_from_har(har_path, not_found="abort")
    await page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page_2.content()
    await expect(page_2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_should_update_har_zip_for_page_with_different_options(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.zip"
    context1 = await browser.new_context()
    page1 = await context1.new_page()
    await page1.route_from_har(
        har_path, update=True, update_content="embed", update_mode="full"
    )
    await page1.goto(server.PREFIX + "/one-style.html")
    await context1.close()

    context2 = await browser.new_context()
    page2 = await context2.new_page()
    await page2.route_from_har(har_path, not_found="abort")
    await page2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page2.content()
    await expect(page2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )
    await context2.close()


async def test_should_update_extracted_har_zip_for_page(
    browser: Browser, server: Server, tmpdir: Path
) -> None:
    har_path = tmpdir / "har.har"
    context = await browser.new_context()
    page_1 = await context.new_page()
    await page_1.route_from_har(har_path, update=True)
    await page_1.goto(server.PREFIX + "/one-style.html")
    await context.close()

    assert har_path.exists()
    with har_path.open() as r:
        content = r.read()
        assert "log" in content
        assert "background-color" not in r.read()

    context_2 = await browser.new_context()
    page_2 = await context_2.new_page()
    await page_2.route_from_har(har_path, not_found="abort")
    await page_2.goto(server.PREFIX + "/one-style.html")
    assert "hello, world!" in await page_2.content()
    await expect(page_2.locator("body")).to_have_css(
        "background-color", "rgb(255, 192, 203)"
    )


async def test_should_ignore_aborted_requests(
    context_factory: Callable[[], Awaitable[BrowserContext]],
    server: Server,
    tmpdir: Path,
) -> None:
    path = tmpdir / "test.har"
    server.set_route("/x", lambda request: request.loseConnection())
    context1 = await context_factory()
    await context1.route_from_har(har=path, update=True)
    page1 = await context1.new_page()
    await page1.goto(server.EMPTY_PAGE)
    req_promise = asyncio.create_task(server.wait_for_request("/x"))
    eval_task = asyncio.create_task(
        page1.evaluate(
            "url => fetch(url).catch(e => 'cancelled')", server.PREFIX + "/x"
        )
    )
    await req_promise
    req = await eval_task
    assert req == "cancelled"
    await context1.close()

    server.reset()

    def _handle_route(req: TestServerRequest) -> None:
        req.setHeader("Content-Type", "text/plain")
        req.write(b"test")
        req.finish()

    server.set_route("/x", _handle_route)
    context2 = await context_factory()
    await context2.route_from_har(path)
    page2 = await context2.new_page()
    await page2.goto(server.EMPTY_PAGE)
    eval_task = asyncio.create_task(
        page2.evaluate(
            "url => fetch(url).catch(e => 'cancelled')", server.PREFIX + "/x"
        )
    )

    async def _timeout() -> str:
        await asyncio.sleep(1)
        return "timeout"

    done, _ = await asyncio.wait(
        [eval_task, asyncio.create_task(_timeout())],
        return_when=asyncio.FIRST_COMPLETED,
    )
    assert next(iter(done)).result() == "timeout"
    eval_task.cancel()
