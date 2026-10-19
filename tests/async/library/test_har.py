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

"""Port of tests/library/har.spec.ts."""

import asyncio
import base64
import contextlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional

import pytest

from playwright._impl._driver import compute_driver_executable
from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    Request,
    Route,
)
from tests.helpers.har import (
    har_time_to_ms,
    parse_har,
    read_har_log,
)
from tests.helpers.http2_server import Http2Server
from tests.server import Server, TestServerRequest
from tests.utils import must

CERT_SUBJECT = "playwright-test"
CERT_VALID_FROM = 1691708270
CERT_VALID_TO = 2007068270

LOCAL_ADDRESS = re.compile(r"^127\.0\.0\.1|\[::1\]")


def now_ms() -> float:
    return time.time() * 1000


class HarPage:
    """The object that pageWithHar() returns upstream."""

    def __init__(self, page: Page, context: BrowserContext, har_path: Path) -> None:
        self.page = page
        self.context = context
        self.har_path = har_path

    async def get_log(self) -> Dict[str, Any]:
        await self.context.close()
        return read_har_log(self.har_path)

    async def get_zip(self) -> Dict[str, bytes]:
        await self.context.close()
        return parse_har(self.har_path)


PageWithHar = Callable[..., Awaitable[HarPage]]


@pytest.fixture
def page_with_har(
    context_factory: Callable[..., Awaitable[BrowserContext]], tmp_path: Path
) -> PageWithHar:
    """Port of pageWithHar() in the upstream file."""

    async def create(
        output_path: Optional[str] = None,
        content: Optional[Literal["attach", "embed", "omit"]] = None,
        omit_content: Optional[bool] = None,
        mode: Optional[Literal["full", "minimal"]] = None,
    ) -> HarPage:
        har_path = tmp_path / (output_path or "test.har")
        context = await context_factory(
            record_har_path=har_path,
            record_har_content=content,
            record_har_omit_content=omit_content,
            record_har_mode=mode,
            ignore_https_errors=True,
        )
        page = await context.new_page()
        return HarPage(page, context, har_path)

    return create


def set_cookie_route(*cookies: str) -> Callable[[TestServerRequest], None]:
    """A route that answers with one Set-Cookie header per cookie and an empty body."""

    def handler(request: TestServerRequest) -> None:
        request.responseHeaders.setRawHeaders("Set-Cookie", list(cookies))
        request.finish()

    return handler


def find_header(headers: List[Dict[str, str]], name: str) -> Optional[Dict[str, str]]:
    return next((h for h in headers if h["name"].lower() == name), None)


async def test_HA_001_should_have_version_and_creator(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    assert log["version"] == "1.2"
    assert log["creator"]["name"] == "Playwright"
    package_json = Path(compute_driver_executable()[1]).parent / "package.json"
    assert (
        os.environ.get("PW_VERSION_OVERRIDE")
        or json.loads(package_json.read_text())["version"]
    ) in log["creator"]["version"]


async def test_HA_002_should_have_browser(
    browser_name: str, browser: Browser, page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()

    assert log["browser"]["name"] == browser_name
    assert log["browser"]["version"] == browser.version


async def test_HA_003_should_have_pages(page_with_har: PageWithHar) -> None:
    har = await page_with_har()
    await har.page.goto("data:text/html,<title>Hello</title>")
    # For data: load comes before domcontentloaded...
    await har.page.wait_for_load_state("domcontentloaded")
    log = await har.get_log()
    assert len(log["pages"]) == 1
    page_entry = log["pages"][0]
    assert page_entry["id"]
    assert page_entry["title"] == "Hello"
    assert har_time_to_ms(page_entry["startedDateTime"]) > now_ms() - 3600 * 1000
    assert page_entry["pageTimings"]["onContentLoad"] > 0
    assert page_entry["pageTimings"]["onLoad"] > 0


async def test_HA_004_should_have_pages_in_persistent_context(
    launch_persistent: Callable[..., Awaitable[Any]], tmp_path: Path
) -> None:
    har_path = tmp_path / "test.har"
    context, page = await launch_persistent(record_har_path=har_path)
    await page.goto("data:text/html,<title>Hello</title>")
    # For data: load comes before domcontentloaded...
    await page.wait_for_load_state("domcontentloaded")
    await context.close()
    log = read_har_log(har_path)
    assert len(log["pages"]) == 1
    page_entry = log["pages"][0]
    assert page_entry["id"]
    assert page_entry["title"] == "Hello"


async def test_HA_005_should_include_request(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    assert len(log["entries"]) == 1
    entry = log["entries"][0]
    assert entry["pageref"] == log["pages"][0]["id"]
    assert entry["request"]["url"] == server.EMPTY_PAGE
    assert entry["request"]["method"] == "GET"
    assert entry["request"]["httpVersion"] == "HTTP/1.1"
    assert len(entry["request"]["headers"]) > 1
    assert find_header(entry["request"]["headers"], "user-agent")
    assert entry["request"]["bodySize"] == 0


async def test_HA_006_should_populate_entry_started_date_time_from_the_browser(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)

    # The browser issues a request after a short delay, then we deliberately
    # block the client. Upstream, this blocks the event loop that records the HAR;
    # here the driver runs in its own process. If `startedDateTime` is populated
    # from the clock at observation time it will land inside the busy-loop window
    # (i.e. close to `unblocked_at`); if it comes from the browser via the
    # debugging protocol it will be tied to when the browser actually sent the request.
    # The driver sends "response" events only while the client listens to them, and
    # here it runs in its own process, so start waiting for the response before the
    # request; upstream waits after the busy loop.
    async with har.page.expect_response("**/delayed-fetch"):
        await har.page.evaluate(
            "() => { window.builtins.setTimeout(() => { void fetch('/delayed-fetch'); }, 50); }"
        )

        block_until = now_ms() + 300
        while now_ms() < block_until:
            # Busy loop to prevent the client from processing protocol events.
            pass
        unblocked_at = now_ms()

    log = await har.get_log()

    entry = next(
        e for e in log["entries"] if e["request"]["url"].endswith("/delayed-fetch")
    )
    started_at = har_time_to_ms(entry["startedDateTime"])
    # The recorded time should be tied to when the browser actually sent the
    # request (during the busy loop), not to when the protocol event was
    # observed (after the busy loop).
    assert started_at < unblocked_at - 100


async def test_HA_007_should_include_response(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    entry = log["entries"][0]
    assert entry["response"]["status"] == 200
    assert entry["response"]["statusText"] == "OK"
    assert entry["response"]["httpVersion"] == "HTTP/1.1"
    assert len(entry["response"]["headers"]) > 1
    content_type = find_header(entry["response"]["headers"], "content-type")
    assert content_type
    assert "text/html" in content_type["value"]


async def test_HA_008_should_include_redirect_url(
    page_with_har: PageWithHar, server: Server
) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/foo.html")
    log = await har.get_log()
    assert len(log["entries"]) == 2
    entry = log["entries"][0]
    assert entry["response"]["status"] == 302
    assert entry["response"]["redirectURL"] == server.EMPTY_PAGE


async def test_HA_009_should_include_query_params(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/har.html?name=value")
    log = await har.get_log()
    assert log["entries"][0]["request"]["queryString"] == [
        {"name": "name", "value": "value"}
    ]


async def test_HA_010_should_include_post_data(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.evaluate("() => fetch('./post', { method: 'POST', body: 'Hello' })")
    log = await har.get_log()
    assert log["entries"][1]["request"]["postData"] == {
        "mimeType": "text/plain;charset=UTF-8",
        "params": [],
        "text": "Hello",
    }


async def test_HA_011_should_include_binary_post_data(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.evaluate(
        """async () => {
            await fetch('./post', { method: 'POST', body: new Uint8Array(Array.from(Array(16).keys())) });
        }"""
    )
    log = await har.get_log()
    assert log["entries"][1]["request"]["postData"] == {
        "mimeType": "application/octet-stream",
        "params": [],
        "text": "",
    }


async def test_HA_012_should_include_form_params(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.set_content(
        "<form method='POST' action='/post'><input type='text' name='foo' value='bar'><input type='number' name='baz' value='123'><input type='submit'></form>"
    )
    await har.page.click("input[type=submit]")
    log = await har.get_log()
    assert log["entries"][1]["request"]["postData"] == {
        "mimeType": "application/x-www-form-urlencoded",
        "params": [
            {"name": "foo", "value": "bar"},
            {"name": "baz", "value": "123"},
        ],
        "text": "foo=bar&baz=123",
    }


async def test_HA_013_should_include_cookies(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    context = har.page.context
    await context.add_cookies(
        [
            {
                "name": "name1",
                "value": '"value1"',
                "domain": "localhost",
                "path": "/",
                "httpOnly": True,
            },
            {
                "name": "name2",
                "value": 'val"ue2',
                "domain": "localhost",
                "path": "/",
                "sameSite": "Lax",
            },
            {"name": "name3", "value": "val=ue3", "domain": "localhost", "path": "/"},
            {"name": "name4", "value": "val,ue4", "domain": "localhost", "path": "/"},
        ]
    )
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    assert log["entries"][0]["request"]["cookies"] == [
        {"name": "name1", "value": '"value1"'},
        {"name": "name2", "value": 'val"ue2'},
        {"name": "name3", "value": "val=ue3"},
        {"name": "name4", "value": "val,ue4"},
    ]


async def test_HA_014_should_include_set_cookies(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    server.set_route(
        "/empty.html",
        set_cookie_route(
            "name1=value1; HttpOnly",
            'name2="value2"',
            "name3=value4; Path=/; Domain=example.com; Max-Age=1500",
        ),
    )
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    cookies = log["entries"][0]["response"]["cookies"]
    assert cookies[0] == {"name": "name1", "value": "value1", "httpOnly": True}
    assert cookies[1] == {"name": "name2", "value": '"value2"'}
    assert har_time_to_ms(cookies[2]["expires"]) > now_ms()


async def test_HA_015_should_include_set_cookies_without_equals_sign_as_nameless(
    page_with_har: PageWithHar, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/43155
    har = await page_with_har()
    server.set_route("/empty.html", set_cookie_route("token; HttpOnly"))
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    assert log["entries"][0]["response"]["cookies"] == [
        {"name": "", "value": "token", "httpOnly": True}
    ]


async def test_HA_016_should_include_set_cookies_with_lowercase_attributes(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    server.set_route(
        "/empty.html",
        set_cookie_route("name=value; path=/; httponly; secure; samesite=Lax"),
    )
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    cookies = log["entries"][0]["response"]["cookies"]
    assert cookies[0] == {
        "name": "name",
        "value": "value",
        "path": "/",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
    }


async def test_HA_017_should_skip_invalid_expires(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    server.set_route(
        "/empty.html",
        set_cookie_route("name=value;Expires=Sat Sep 14 01:02:27 CET 2024"),
    )
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    cookies = log["entries"][0]["response"]["cookies"]
    assert cookies[0] == {"name": "name", "value": "value"}


async def test_HA_018_should_include_set_cookies_with_comma(
    page_with_har: PageWithHar, server: Server, browser_name: str
) -> None:
    if browser_name == "webkit":
        pytest.skip('fixme: We get "name1=val, ue1, name2=val, ue2" as a header value')
    har = await page_with_har()
    server.set_route(
        "/empty.html", set_cookie_route("name1=val, ue1", "name2=val, ue2")
    )
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    cookies = log["entries"][0]["response"]["cookies"]
    assert cookies[0] == {"name": "name1", "value": "val, ue1"}
    assert cookies[1] == {"name": "name2", "value": "val, ue2"}


async def test_HA_019_should_include_secure_set_cookies(
    page_with_har: PageWithHar, https_server: Server
) -> None:
    har = await page_with_har()
    https_server.set_route("/empty.html", set_cookie_route("name1=value1; Secure"))
    await har.page.goto(https_server.EMPTY_PAGE)
    log = await har.get_log()
    cookies = log["entries"][0]["response"]["cookies"]
    assert cookies[0] == {"name": "name1", "value": "value1", "secure": True}


async def test_HA_020_should_record_request_overrides(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()

    async def handle(route: Route) -> None:
        await route.fallback(
            url=server.EMPTY_PAGE,
            method="POST",
            headers={
                **route.request.headers,
                "content-type": "text/plain",
                "cookie": "foo=bar",
                "custom": "value",
            },
            post_data="Hi!",
        )

    await har.page.route("**/foo", handle)

    await har.page.goto(server.PREFIX + "/foo")
    log = await har.get_log()
    request = log["entries"][0]["request"]
    assert request["url"] == server.EMPTY_PAGE
    assert request["method"] == "POST"
    assert {"name": "custom", "value": "value"} in request["headers"]
    assert request["cookies"] == []
    assert request["postData"] == {
        "mimeType": "text/plain",
        "params": [],
        "text": "Hi!",
    }


async def test_HA_021_should_include_content_smoke(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/har.html")
    await har.page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    log = await har.get_log()

    content = log["entries"][0]["response"]["content"]
    assert "encoding" not in content
    assert content["mimeType"] == "text/html; charset=utf-8"
    assert "HAR Page" in content["text"]
    assert content["size"] >= 96
    assert content["compression"] == 0

    content = log["entries"][1]["response"]["content"]
    assert "encoding" not in content
    assert content["mimeType"] == "text/css; charset=utf-8"
    assert "pink" in content["text"]
    assert content["size"] >= 37
    assert content["compression"] == 0

    content = log["entries"][2]["response"]["content"]
    assert content["encoding"] == "base64"
    assert content["mimeType"] == "image/png"
    assert len(base64.b64decode(content["text"])) > 0
    assert content["size"] >= 6000
    assert content["compression"] == 0


async def test_HA_022_should_use_attach_mode_for_zip_extension(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har(output_path="test.har.zip")
    await har.page.goto(server.PREFIX + "/har.html")
    await har.page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    zip = await har.get_zip()
    log = json.loads(zip["har.har"])["log"]
    assert "text" not in log["entries"][0]["response"]["content"]
    assert b"HAR Page" in zip["75841480e2606c03389077304342fac2c58ccb1b.html"]


async def test_HA_023_should_omit_content(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har(content="omit", output_path="test.har")
    await har.page.goto(server.PREFIX + "/har.html")
    await har.page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    log = await har.get_log()
    assert "text" not in log["entries"][0]["response"]["content"]
    assert "_file" not in log["entries"][0]["response"]["content"]


async def test_HA_024_should_omit_content_legacy(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har(omit_content=True, output_path="test.har")
    await har.page.goto(server.PREFIX + "/har.html")
    await har.page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    log = await har.get_log()
    assert "text" not in log["entries"][0]["response"]["content"]
    assert "_file" not in log["entries"][0]["response"]["content"]


async def test_HA_025_should_attach_content(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har(content="attach", output_path="test.har.zip")
    await har.page.goto(server.PREFIX + "/har.html")
    await har.page.evaluate("() => fetch('/pptr.png').then(r => r.arrayBuffer())")
    zip = await har.get_zip()
    log = json.loads(zip["har.har"])["log"]

    content = log["entries"][0]["response"]["content"]
    assert "encoding" not in content
    assert content["mimeType"] == "text/html; charset=utf-8"
    assert "75841480e2606c03389077304342fac2c58ccb1b" in content["_file"]
    assert content["size"] >= 96
    assert content["compression"] == 0

    content = log["entries"][1]["response"]["content"]
    assert "encoding" not in content
    assert content["mimeType"] == "text/css; charset=utf-8"
    assert "79f739d7bc88e80f55b9891a22bf13a2b4e18adb" in content["_file"]
    assert content["size"] >= 37
    assert content["compression"] == 0

    content = log["entries"][2]["response"]["content"]
    assert "encoding" not in content
    assert content["mimeType"] == "image/png"
    assert "a4c3a18f0bb83f5d9fe7ce561e065c36205762fa" in content["_file"]
    assert content["size"] >= 6000
    assert content["compression"] == 0

    assert b"HAR Page" in zip["75841480e2606c03389077304342fac2c58ccb1b.html"]
    assert b"pink" in zip["79f739d7bc88e80f55b9891a22bf13a2b4e18adb.css"]
    assert (
        len(zip["a4c3a18f0bb83f5d9fe7ce561e065c36205762fa.png"])
        == log["entries"][2]["response"]["content"]["size"]
    )


async def test_HA_026_should_filter_by_glob(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "test.har"
    context = await context_factory(
        base_url=server.PREFIX,
        record_har_path=har_path,
        record_har_url_filter="/*.css",
        ignore_https_errors=True,
    )
    page = await context.new_page()
    await page.goto("/har.html")
    await context.close()
    log = read_har_log(har_path)
    assert len(log["entries"]) == 1
    assert log["entries"][0]["request"]["url"].endswith("one-style.css")


async def test_HA_027_should_filter_by_regexp(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    har_path = tmp_path / "test.har"
    context = await context_factory(
        record_har_path=har_path,
        record_har_url_filter=re.compile("HAR.X?HTML", re.IGNORECASE),
        ignore_https_errors=True,
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/har.html")
    await context.close()
    log = read_har_log(har_path)
    assert len(log["entries"]) == 1
    assert log["entries"][0]["request"]["url"].endswith("har.html")


async def test_HA_028_should_include_sizes(
    page_with_har: PageWithHar, server: Server, assetdir: Path
) -> None:
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/har.html")
    log = await har.get_log()
    assert len(log["entries"]) == 2
    assert log["entries"][0]["request"]["url"].endswith("har.html")
    assert log["entries"][0]["request"]["headersSize"] >= 100
    assert (
        log["entries"][0]["response"]["bodySize"]
        == (assetdir / "har.html").stat().st_size
    )
    assert log["entries"][0]["response"]["headersSize"] >= 100
    assert log["entries"][0]["response"]["_transferSize"] >= 250

    assert log["entries"][1]["request"]["url"].endswith("one-style.css")
    assert (
        log["entries"][1]["response"]["bodySize"]
        == (assetdir / "one-style.css").stat().st_size
    )
    assert log["entries"][1]["response"]["headersSize"] >= 100
    assert log["entries"][1]["response"]["_transferSize"] >= 150


async def test_HA_029_should_work_with_gzip_compression(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    server.enable_gzip("/simplezip.json")
    response = await har.page.goto(server.PREFIX + "/simplezip.json")
    assert response
    assert response.headers["content-encoding"] == "gzip"
    log = await har.get_log()
    assert len(log["entries"]) == 1
    assert log["entries"][0]["response"]["content"]["compression"] > 4000


async def test_HA_030_should_calculate_time(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/har.html")
    log = await har.get_log()
    assert log["entries"][0]["time"] > 0


async def test_HA_031_should_return_receive_time(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/har.html")
    log = await har.get_log()
    assert log["entries"][0]["timings"]["receive"] > 0


async def test_HA_032_should_report_the_correct_transfer_size_with_png_files(
    page_with_har: PageWithHar, server: Server, assetdir: Path
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.set_content(
        f"""
    <img src="{server.PREFIX}/pptr.png" />
  """
    )
    log = await har.get_log()
    assert (
        log["entries"][1]["response"]["_transferSize"]
        > (assetdir / "pptr.png").stat().st_size
    )


async def test_HA_033_should_have_1_transfer_size_when_its_a_failed_request(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()

    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")
        request.loseConnection()

    server.set_route("/one-style.css", handle)
    failed_requests: List[Request] = []
    har.page.on("requestfailed", lambda request: failed_requests.append(request))
    await har.page.goto(server.PREFIX + "/har.html")
    log = await har.get_log()
    assert log["entries"][1]["request"]["url"].endswith("/one-style.css")
    assert log["entries"][1]["response"]["_transferSize"] == -1


async def test_HA_034_should_record_failed_request_headers(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    server.set_route("/har.html", lambda request: request.loseConnection())
    with contextlib.suppress(Error):
        await har.page.goto(server.PREFIX + "/har.html")
    log = await har.get_log()
    assert log["entries"][0]["response"]["_failureText"]
    request = log["entries"][0]["request"]
    assert request["url"].endswith("/har.html")
    assert request["method"] == "GET"
    assert any(header["name"] == "User-Agent" for header in request["headers"])


async def test_HA_035_should_record_failed_request_overrides(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    server.set_route("/empty.html", lambda request: request.loseConnection())

    async def handle(route: Route) -> None:
        await route.fallback(
            url=server.EMPTY_PAGE,
            method="POST",
            headers={
                **route.request.headers,
                "content-type": "text/plain",
                "cookie": "foo=bar",
                "custom": "value",
            },
            post_data="Hi!",
        )

    await har.page.route("**/foo", handle)
    with contextlib.suppress(Error):
        await har.page.goto(server.PREFIX + "/foo")
    log = await har.get_log()
    assert log["entries"][0]["response"]["_failureText"]
    request = log["entries"][0]["request"]
    assert request["url"] == server.EMPTY_PAGE
    assert request["method"] == "POST"
    assert {"name": "custom", "value": "value"} in request["headers"]
    assert request["cookies"] == []
    assert request["postData"] == {
        "mimeType": "text/plain",
        "params": [],
        "text": "Hi!",
    }


async def test_HA_036_should_report_the_correct_request_body_size(
    page_with_har: PageWithHar, server: Server
) -> None:
    server.set_route("/api", lambda request: request.finish())
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    async with har.page.expect_response(server.PREFIX + "/api1"):
        await har.page.evaluate(
            """() => {
                void fetch('/api1', {
                    method: 'POST',
                    body: 'abc123'
                });
            }"""
        )
    log = await har.get_log()
    assert log["entries"][1]["request"]["bodySize"] == 6


async def test_HA_037_should_report_the_correct_request_body_size_when_the_body_size_is_0(
    page_with_har: PageWithHar, server: Server
) -> None:
    server.set_route("/api", lambda request: request.finish())
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    async with har.page.expect_response(server.PREFIX + "/api2"):
        await har.page.evaluate(
            """() => {
                void fetch('/api2', {
                    method: 'POST',
                    body: ''
                });
            }"""
        )
    log = await har.get_log()
    assert log["entries"][1]["request"]["bodySize"] == 0


async def test_HA_038_should_report_the_correct_response_body_size_when_the_body_size_is_0(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    response = await har.page.goto(server.EMPTY_PAGE)
    assert response
    await response.finished()
    log = await har.get_log()
    assert log["entries"][0]["response"]["bodySize"] == 0


async def test_HA_039_should_have_popup_requests(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.set_content(
        '<a target=_blank rel=noopener href="/one-style.html">yo</a>'
    )
    async with har.page.expect_popup() as popup_info:
        await har.page.click("a")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    log = await har.get_log()

    assert len(log["pages"]) == 2

    entries = [
        entry for entry in log["entries"] if entry["pageref"] == log["pages"][1]["id"]
    ]
    assert len(entries) == 2
    assert entries[0]["request"]["url"] == server.PREFIX + "/one-style.html"
    assert entries[0]["response"]["status"] == 200
    assert entries[1]["request"]["url"] == server.PREFIX + "/one-style.css"
    assert entries[1]["response"]["status"] == 200


async def test_HA_040_should_not_contain_internal_pages(
    page_with_har: PageWithHar, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/6743
    server.set_route("/empty.html", set_cookie_route("name=value"))

    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)

    cookies = await har.context.cookies()
    assert len(cookies) == 1
    # Get storage state, this create internal page.
    await har.context.storage_state()

    log = await har.get_log()
    assert len(log["pages"]) == 1


async def test_HA_041_should_have_connection_details(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    log = await har.get_log()
    entry = log["entries"][0]
    assert LOCAL_ADDRESS.search(entry["serverIPAddress"])
    assert entry["_serverPort"] == server.PORT
    assert entry["_securityDetails"] == {}


async def test_HA_042_should_have_security_details(
    page_with_har: PageWithHar,
    https_server: Server,
    browser_name: str,
    platform: str,
    browser_channel: Optional[str],
    is_frozen_webkit: bool,
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> None:
    if (
        browser_name == "webkit"
        and platform == "win32"
        and browser_channel != "webkit-wsl"
    ):
        request.applymarker(
            pytest.mark.xfail(
                reason="upstream: fails on WebKit on Windows", strict=True
            )
        )
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    har = await page_with_har()
    api_har_path = tmp_path / "api.har"
    await har.context.request.tracing.start_har(api_har_path)
    await har.page.goto(https_server.EMPTY_PAGE)
    await har.page.request.get(https_server.EMPTY_PAGE)
    await har.context.request.tracing.stop_har()
    log = await har.get_log()
    assert len(log["entries"]) == 1
    entry = log["entries"][0]
    assert LOCAL_ADDRESS.search(entry["serverIPAddress"])
    assert entry["_serverPort"] == https_server.PORT
    if browser_name == "webkit":
        assert entry["_securityDetails"] == {
            "protocol": "TLS 1.3",
            "subjectName": CERT_SUBJECT,
            "validFrom": CERT_VALID_FROM,
            "validTo": CERT_VALID_TO,
        }
    else:
        assert entry["_securityDetails"] == {
            "issuer": CERT_SUBJECT,
            "protocol": "TLS 1.3",
            "subjectName": CERT_SUBJECT,
            "validFrom": CERT_VALID_FROM,
            "validTo": CERT_VALID_TO,
        }

    api_log = read_har_log(api_har_path)
    assert len(api_log["entries"]) == 1
    assert api_log["entries"][0]["_securityDetails"] == {
        "issuer": CERT_SUBJECT,
        "protocol": "TLSv1.3",
        "subjectName": CERT_SUBJECT,
        "validFrom": CERT_VALID_FROM,
        "validTo": CERT_VALID_TO,
    }


async def test_HA_043_should_have_connection_details_for_redirects(
    page_with_har: PageWithHar, server: Server, browser_name: str
) -> None:
    server.set_redirect("/foo.html", "/empty.html")
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/foo.html")
    log = await har.get_log()
    assert len(log["entries"]) == 2

    details_foo = log["entries"][0]

    if browser_name == "webkit":
        assert "serverIPAddress" not in details_foo
        assert "_serverPort" not in details_foo
    else:
        assert LOCAL_ADDRESS.search(details_foo["serverIPAddress"])
        assert details_foo["_serverPort"] == server.PORT

    details_empty = log["entries"][1]
    assert LOCAL_ADDRESS.search(details_empty["serverIPAddress"])
    assert details_empty["_serverPort"] == server.PORT


async def test_HA_044_should_have_connection_details_for_failed_requests(
    page_with_har: PageWithHar, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/css")
        request.loseConnection()

    server.set_route("/one-style.css", handle)
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/one-style.html")
    log = await har.get_log()
    entry = log["entries"][0]
    assert LOCAL_ADDRESS.search(entry["serverIPAddress"])
    assert entry["_serverPort"] == server.PORT


async def test_HA_045_should_return_server_address_directly_from_response(
    page: Page, server: Server
) -> None:
    response = await page.goto(server.EMPTY_PAGE)
    assert response
    server_addr = await response.server_addr()
    assert server_addr
    assert LOCAL_ADDRESS.search(server_addr["ipAddress"])
    assert server_addr["port"] == server.PORT


async def test_HA_046_should_return_security_details_directly_from_response(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    https_server: Server,
    browser_name: str,
    platform: str,
    is_frozen_webkit: bool,
) -> None:
    if is_frozen_webkit:
        pytest.skip("frozen WebKit")

    context = await context_factory(ignore_https_errors=True)
    page = await context.new_page()
    response = await page.goto(https_server.EMPTY_PAGE)
    assert response
    security_details = await response.security_details()
    if browser_name == "webkit" and platform == "win32":
        # WebKit on Windows does not surface the TLS protocol.
        assert {
            key: value
            for key, value in must(security_details).items()
            if key != "protocol"
        } == {
            "subjectName": CERT_SUBJECT,
            "validFrom": CERT_VALID_FROM,
            "validTo": CERT_VALID_TO,
        }
    elif browser_name == "webkit":
        assert security_details == {
            "protocol": "TLS 1.3",
            "subjectName": CERT_SUBJECT,
            "validFrom": CERT_VALID_FROM,
            "validTo": CERT_VALID_TO,
        }
    else:
        assert security_details == {
            "issuer": CERT_SUBJECT,
            "protocol": "TLS 1.3",
            "subjectName": CERT_SUBJECT,
            "validFrom": CERT_VALID_FROM,
            "validTo": CERT_VALID_TO,
        }


async def test_HA_047_should_contain_http2_for_http2_requests(
    page_with_har: PageWithHar,
) -> None:
    http2_server = Http2Server(
        headers=[(":status", "200"), ("content-type", "text/html; charset=utf-8")],
        body=b"<h1>Hello World</h1>",
    )
    try:
        har = await page_with_har()
        await har.page.goto(f"https://localhost:{http2_server.port}")
        log = await har.get_log()
        assert log["entries"][0]["request"]["httpVersion"] == "HTTP/2.0"
        assert log["entries"][0]["response"]["httpVersion"] == "HTTP/2.0"
        assert (
            log["entries"][0]["response"]["content"]["text"] == "<h1>Hello World</h1>"
        )
    finally:
        http2_server.close()


async def test_HA_048_should_filter_favicon_and_favicon_redirects(
    server: Server,
    browser_name: str,
    headless: bool,
    assetdir: Path,
    page_with_har: PageWithHar,
) -> None:
    if headless and browser_name != "firefox":
        pytest.skip("headless browsers, except firefox, do not request favicons")
    if not headless and browser_name == "webkit":
        pytest.skip("headed webkit does not have a favicon feature")

    har = await page_with_har()

    # Browsers aggressively cache favicons, so force bust with the
    # `d` parameter to make iterating on this test more predictable and isolated.
    favicon = "/no-cache-2/favicon.ico"
    hashed_favicon_url = "/favicon-hashed.ico"
    server.set_redirect(favicon, hashed_favicon_url)
    server.set_route(
        hashed_favicon_url,
        lambda request: request.serve_file(
            assetdir / "media-query-prefers-color-scheme.svg"
        ),
    )

    def handle_page(request: TestServerRequest) -> None:
        request.write(
            f"""
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <link rel="icon" type="image/svg+xml" href="{favicon}">
          <title>SVG Favicon Test</title>
        </head>
        <body>
          favicons
        </body>
      </html>
""".encode()
        )
        request.finish()

    server.set_route("/page.html", handle_page)

    with server.expect_request(favicon) as favicon_request:
        with server.expect_request(hashed_favicon_url) as hashed_favicon_request:
            await har.page.goto(server.PREFIX + "/page.html")

    await har.page.wait_for_timeout(500)
    assert favicon_request.value
    assert hashed_favicon_request.value
    # Text still being around ensures we haven't actually lost our browser to a crash.
    await har.page.wait_for_selector("text=favicons")

    # favicon and 302 redirects to favicons should be filtered out of request logs
    log = await har.get_log()
    assert len(log["entries"]) == 1
    entry = log["entries"][0]
    assert entry["request"]["url"] == server.PREFIX + "/page.html"


async def test_HA_049_should_have_different_hars_for_concurrent_contexts(
    page_with_har: PageWithHar,
) -> None:
    session0 = await page_with_har(output_path="test-0.har")
    await session0.page.goto("data:text/html,<title>Zero</title>")
    await session0.page.wait_for_load_state("domcontentloaded")

    session1 = await page_with_har(output_path="test-1.har")
    await session1.page.goto("data:text/html,<title>One</title>")
    await session1.page.wait_for_load_state("domcontentloaded")

    # Trigger flushing on the server and ensure they are not racing to same
    # location. NB: Run this test with --count 10.
    log0, log1 = await asyncio.gather(session0.get_log(), session1.get_log())

    assert len(log0["pages"]) == 1
    page_entry = log0["pages"][0]
    assert page_entry["title"] == "Zero"

    assert len(log1["pages"]) == 1
    page_entry = log1["pages"][0]
    assert page_entry["id"] != log0["pages"][0]["id"]
    assert page_entry["title"] == "One"


async def test_HA_050_should_exclude_api_request(
    page_with_har: PageWithHar, server: Server
) -> None:
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.request.get(server.PREFIX + "/simple.json")
    log = await har.get_log()
    assert [entry["request"]["url"] for entry in log["entries"]] == [server.EMPTY_PAGE]


async def test_HA_051_should_correctly_record_api_request_cookies_with_equals_sign_in_value(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    context = await context_factory()
    har_path = tmp_path / "request.har"
    await context.request.tracing.start_har(har_path)
    url = server.PREFIX + "/simple.json"
    await context.request.get(url, headers={"cookie": "token=abc=xyz; other=val"})
    await context.request.tracing.stop_har()
    await context.close()
    log = read_har_log(har_path)
    assert log["entries"][0]["request"]["cookies"] == [
        {"name": "token", "value": "abc=xyz"},
        {"name": "other", "value": "val"},
    ]


async def test_HA_052_should_record_nameless_api_request_cookies(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/43155
    context = await context_factory()
    har_path = tmp_path / "request.har"
    await context.request.tracing.start_har(har_path)
    await context.request.get(
        server.PREFIX + "/simple.json", headers={"cookie": "nameless; other=val"}
    )
    await context.request.tracing.stop_har()
    await context.close()
    log = read_har_log(har_path)
    assert log["entries"][0]["request"]["cookies"] == [
        {"name": "", "value": "nameless"},
        {"name": "other", "value": "val"},
    ]


async def test_HA_053_should_respect_minimal_mode_for_api_requests(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    context = await context_factory()
    har_path = tmp_path / "request.har"
    await context.request.tracing.start_har(har_path, mode="minimal")
    url = server.PREFIX + "/simple.json"
    await context.request.post(url, headers={"cookie": "a=b; c=d"}, data={"foo": "bar"})
    await context.request.tracing.stop_har()
    await context.close()
    entries = read_har_log(har_path)["entries"]
    assert len(entries) == 1
    [entry] = entries
    assert entry["timings"] == {"receive": -1, "send": -1, "wait": -1}
    assert "serverIPAddress" not in entry
    assert "_serverPort" not in entry
    assert entry["request"]["cookies"] == []
    assert entry["request"]["bodySize"] == -1
    assert entry["response"]["bodySize"] == -1


async def test_HA_054_should_include_redirects_from_api_request(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    server.set_redirect("/redirect-me", "/simple.json")
    context = await context_factory()
    har_path = tmp_path / "request.har"
    await context.request.tracing.start_har(har_path)
    await context.request.post(
        server.PREFIX + "/redirect-me",
        headers={"cookie": "a=b; c=d"},
        data={"foo": "bar"},
    )
    await context.request.tracing.stop_har()
    await context.close()
    log = read_har_log(har_path)
    assert len(log["entries"]) == 2
    redirect, json_entry = log["entries"]
    assert redirect["request"]["url"] == server.PREFIX + "/redirect-me"
    assert json_entry["request"]["url"] == server.PREFIX + "/simple.json"
    assert redirect["response"]["bodySize"] == -1
    assert redirect["response"]["content"]["size"] == -1
    assert "timings" in redirect
    assert "timings" in json_entry


async def test_HA_055_should_not_hang_on_resources_served_from_cache(
    page_with_har: PageWithHar, server: Server, browser_name: str
) -> None:
    # https://github.com/microsoft/playwright/issues/11435
    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/css")
        request.setHeader("Cache-Control", "public, max-age=10031518")
        request.write(b"body { background: red }")
        request.finish()

    server.set_route("/one-style.css", handle)
    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/har.html")
    await har.page.goto(server.PREFIX + "/har.html")
    log = await har.get_log()
    entries = [
        e for e in log["entries"] if e["request"]["url"].endswith("one-style.css")
    ]
    # In firefox no request events are fired for cached resources.
    if browser_name == "firefox":
        assert len(entries) == 1
    else:
        assert len(entries) == 2


async def test_HA_056_should_not_hang_on_slow_chunked_response(
    browser_name: str, browser: Browser, page_with_har: PageWithHar, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/21182
    def handle_page(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""<script>
    let receivedFirstData = new Promise(f => {
      setTimeout(() =>  {
        var x = new XMLHttpRequest();
        x.open("GET", "slow.txt");
        x.onprogress = () => f();
        x.send();
      }, 0);
    });
    </script>"""
        )
        request.finish()

    def handle_slow(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/plain")
        request.setHeader("Transfer-Encoding", "chunked")
        request.setHeader("Content-length", "2023")
        # The headers above stop the server from chunking, so write the chunk as is.
        request.write(b"5\r\nbegin\r\n")

    server.set_route("/empty.html", handle_page)
    server.set_route("/slow.txt", handle_slow)
    har = await page_with_har()
    await har.page.goto(server.EMPTY_PAGE)
    await har.page.evaluate("() => window.receivedFirstData")
    log = await har.get_log()

    assert log["browser"]["name"] == browser_name
    assert log["browser"]["version"] == browser.version


async def test_HA_057_should_close_the_context_when_saving_the_har_fails(
    browser_type: BrowserType,
    launch_arguments: Dict,
    server: Server,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/42231
    # A browser of its own: while the bug is there, the context stays open, and it
    # must not reach the tests that count the contexts of the shared browser.
    browser = await browser_type.launch(**launch_arguments)
    try:
        file_path = tmp_path / "not-a-directory"
        file_path.write_text("data")
        context = await browser.new_context(record_har_path=file_path / "test.har")
        page = await context.new_page()
        await page.goto(server.EMPTY_PAGE)
        async with context.expect_event("close"):
            with pytest.raises(Error, match=r"ENOTDIR|ENOENT|EEXIST"):
                await context.close()
        await context.close()
    finally:
        await browser.close()


async def test_HA_058_should_support_har_larger_than_512_mb(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    browser_name: str,
    tmp_path: Path,
) -> None:
    # https://github.com/microsoft/playwright/issues/36707
    if browser_name != "chromium":
        pytest.skip("serializer is browser-agnostic; one browser is enough")

    har_path = tmp_path / "test.har"
    context = await context_factory()
    await context.request.tracing.start_har(har_path)

    # 30 x 20MB textual responses push the HAR JSON past V8's ~512MB max
    # string length. Each body still fits in a single string; only the
    # aggregate would overflow the previous tokens.join('').
    body = b"a" * (20 * 1024 * 1024)

    def handle(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/plain")
        request.write(body)
        request.finish()

    server.set_route("/large", handle)
    for _ in range(30):
        await context.request.get(f"{server.PREFIX}/large")
    await context.request.tracing.stop_har()
    await context.close()

    size = har_path.stat().st_size
    assert size > 512 * 1024 * 1024

    # Sample the head and tail to verify structural sanity.
    with har_path.open("rb") as file:
        head = file.read(64)
        file.seek(size - 64)
        tail = file.read(64)
    assert re.search(r"^\{\s*\"log\"\s*:\s*\{", head.decode())
    assert re.search(r"\}\s*\}\s*$", tail.decode())


async def test_HA_059_should_record_resource_type(
    page_with_har: PageWithHar, server: Server, assetdir: Path
) -> None:
    def handle_page(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""
      <link rel="stylesheet" href="/resource-type-stylesheet.css">
      <script src="/resource-type-script.js"></script>
      <img src="/resource-type-image.png">
    """
        )
        request.finish()

    def handle_stylesheet(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "text/css")
        request.write(
            b"""
      @font-face {
        font-family: 'iconfont';
        src: url('/resource-type-font.woff2') format('woff2');
      }
      body { font-family: 'iconfont'; }
    """
        )
        request.finish()

    def handle_script(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader("Content-Type", "application/javascript")
        request.write(b"window.__loaded = true;")
        request.finish()

    server.set_route("/resource-types.html", handle_page)
    server.set_route("/resource-type-stylesheet.css", handle_stylesheet)
    server.set_route(
        "/resource-type-font.woff2",
        lambda request: request.serve_file(assetdir / "webfont" / "iconfont.woff2"),
    )
    server.set_route("/resource-type-script.js", handle_script)
    server.set_route(
        "/resource-type-image.png",
        lambda request: request.serve_file(assetdir / "pptr.png"),
    )

    har = await page_with_har()
    await har.page.goto(server.PREFIX + "/resource-types.html")
    await har.page.evaluate("() => fetch('/resource-type-fetch').catch(() => {})")
    await har.page.evaluate(
        """() => new Promise(resolve => {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', '/resource-type-xhr');
            xhr.onloadend = () => resolve();
            xhr.send();
        })"""
    )
    log = await har.get_log()

    type_for_url = {
        entry["request"]["url"]: entry.get("_resourceType") for entry in log["entries"]
    }
    expected = {
        server.PREFIX + "/resource-types.html": "document",
        server.PREFIX + "/resource-type-stylesheet.css": "stylesheet",
        server.PREFIX + "/resource-type-script.js": "script",
        server.PREFIX + "/resource-type-image.png": "image",
        server.PREFIX + "/resource-type-font.woff2": "font",
        server.PREFIX + "/resource-type-fetch": "fetch",
        server.PREFIX + "/resource-type-xhr": "xhr",
    }
    assert {url: type_for_url.get(url) for url in expected} == expected


async def test_HA_060_tracing_start_har_should_record_a_har_with_options(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    context = await context_factory()
    har_path = tmp_path / "tracing.har"
    await context.tracing.start_har(
        har_path, mode="minimal", url_filter="**/one-style.css"
    )
    page = await context.new_page()
    await page.goto(server.PREFIX + "/one-style.html")
    await context.tracing.stop_har()
    await context.close()

    log = read_har_log(har_path)
    urls = [e["request"]["url"] for e in log["entries"]]
    assert urls == [server.PREFIX + "/one-style.css"]
    # Minimal mode drops body sizes.
    assert log["entries"][0]["request"]["bodySize"] == -1


async def test_HA_061_tracing_start_har_should_record_a_har_for_a_context_api_request_context(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    context = await context_factory()
    har_path = tmp_path / "request.har"
    await context.request.tracing.start_har(har_path)
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    url = server.PREFIX + "/simple.json"
    response = await context.request.post(
        url, headers={"cookie": "a=b; c=d"}, data={"foo": "bar"}
    )
    response_body = await response.body()
    await context.request.tracing.stop_har()
    await context.close()

    log = read_har_log(har_path)
    assert len(log["entries"]) == 1
    entry = log["entries"][0]
    assert entry["request"]["url"] == url
    assert entry["request"]["method"] == "POST"
    assert entry["request"]["httpVersion"] == "HTTP/1.1"
    assert entry["request"]["cookies"] == [
        {"name": "a", "value": "b"},
        {"name": "c", "value": "d"},
    ]
    assert len(entry["request"]["headers"]) > 1
    assert find_header(entry["request"]["headers"], "user-agent")
    content_type = find_header(entry["request"]["headers"], "content-type")
    assert content_type and content_type["value"] == "application/json"
    content_length = find_header(entry["request"]["headers"], "content-length")
    assert content_length and content_length["value"] == "13"
    assert entry["request"]["bodySize"] == 13

    assert entry["response"]["status"] == 200
    content_type = find_header(entry["response"]["headers"], "content-type")
    assert content_type and "application/json" in content_type["value"]
    assert entry["response"]["content"]["size"] == 15
    assert entry["response"]["content"]["text"] == response_body.decode()
    assert entry["response"]["bodySize"] == 15

    assert entry["time"] > 0
    timings = entry["timings"]
    assert timings["blocked"] == -1
    for name in ["connect", "dns", "receive", "send", "ssl", "wait"]:
        assert isinstance(timings[name], (int, float)) and not isinstance(
            timings[name], bool
        )

    assert "serverIPAddress" in entry
    assert entry["_serverPort"] == server.PORT


async def test_HA_062_tracing_start_har_should_include_pages(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    server: Server,
    tmp_path: Path,
) -> None:
    context = await context_factory()
    har_path = tmp_path / "tracing.har"
    await context.tracing.start_har(har_path)
    page = await context.new_page()
    await page.goto(server.PREFIX + "/title.html")
    page2 = await context.new_page()
    await page2.goto(server.PREFIX + "/empty.html")
    # Close the page before stopping - it should still be in the har.
    await page.close()
    await context.tracing.stop_har()
    await context.close()

    log = read_har_log(har_path)
    assert len(log["pages"]) == 2
    assert log["pages"][0]["title"] == "Woof-Woof"
    assert log["pages"][1]["title"] == ""


async def test_HA_063_tracing_start_har_should_record_a_zipped_har_for_api_request_context(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    request = await playwright.request.new_context()
    har_path = tmp_path / "tracing.har.zip"
    await request.tracing.start_har(har_path, content="attach")
    await request.get(server.PREFIX + "/simple.json")
    await request.tracing.stop_har()
    await request.dispose()

    resources = parse_har(har_path)
    log = json.loads(resources["har.har"])["log"]
    assert any(
        e["request"]["url"] == server.PREFIX + "/simple.json" for e in log["entries"]
    )


async def test_HA_064_tracing_start_har_should_record_correct_cookie_expires_for_api_request_context(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader(
            "Set-Cookie", "name=value; Expires=Tue, 01 Jan 2030 00:00:00 GMT"
        )
        request.write(b"hello")
        request.finish()

    server.set_route("/set-cookie", handle)
    request = await playwright.request.new_context()
    har_path = tmp_path / "api.har.zip"
    await request.tracing.start_har(har_path, content="attach")
    await request.get(server.PREFIX + "/set-cookie")
    await request.tracing.stop_har()
    await request.dispose()

    resources = parse_har(har_path)
    log = json.loads(resources["har.har"])["log"]
    entry = next(
        e for e in log["entries"] if e["request"]["url"].endswith("/set-cookie")
    )
    cookie = next(c for c in entry["response"]["cookies"] if c["name"] == "name")
    expires = datetime.fromtimestamp(
        har_time_to_ms(cookie["expires"]) / 1000, timezone.utc
    )
    assert expires.year == 2030


async def test_HA_065_tracing_start_har_should_record_mixed_case_request_content_type_for_api_request_context(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.write(b"ok")
        request.finish()

    server.set_route("/post", handle)
    request = await playwright.request.new_context()
    har_path = tmp_path / "api-post.har.zip"
    await request.tracing.start_har(har_path, content="attach")
    await request.post(
        server.PREFIX + "/post",
        headers={"Content-Type": "application/json"},
        data=b'{"a":1}',
    )
    await request.tracing.stop_har()
    await request.dispose()

    resources = parse_har(har_path)
    log = json.loads(resources["har.har"])["log"]
    entry = next(e for e in log["entries"] if e["request"]["url"].endswith("/post"))
    assert entry["request"]["postData"]["mimeType"] == "application/json"
