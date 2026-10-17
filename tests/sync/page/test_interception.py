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

"""Port of tests/page/interception.spec.ts."""

import re
from typing import Callable, Dict, Pattern

import pytest

from playwright._impl._url_match import glob_to_regex_pattern, url_matches
from playwright.sync_api import Error, Page, Request, Route, expect
from tests.server import Server, TestServerRequest


def end(body: str) -> Callable[[TestServerRequest], None]:
    """A server route that answers with body, like upstream's res.end(body)."""

    def handler(request: TestServerRequest) -> None:
        request.write(body.encode())
        request.finish()

    return handler


def test_RO_151_should_work_with_navigation_smoke(page: Page, server: Server) -> None:
    requests: Dict[str, Request] = {}

    def handler(route: Route) -> None:
        requests[route.request.url.split("/").pop()] = route.request
        route.continue_()

    page.route("**/*", handler)
    server.set_redirect("/rrredirect", "/frames/one-frame.html")
    page.goto(server.PREFIX + "/rrredirect")
    assert requests["rrredirect"].is_navigation_request() is True
    assert requests["frame.html"].is_navigation_request() is True
    assert requests["script.js"].is_navigation_request() is False
    assert requests["style.css"].is_navigation_request() is False


def test_RO_152_should_intercept_after_a_service_worker(
    page: Page, server: Server, browser_name: str
) -> None:
    page.goto(server.PREFIX + "/serviceworkers/fetchdummy/sw.html")
    page.evaluate("() => window['activationPromise']")

    # Sanity check.
    sw_response = page.evaluate("() => window['fetchDummy']('foo')")
    assert sw_response == "responseFromServiceWorker:foo"

    def handler(route: Route) -> None:
        name = route.request.url.split("/")[-1]
        route.fulfill(
            status=200,
            content_type="text/css",
            body="responseFromInterception:" + name,
        )

    page.route("**/foo", handler)

    # Page route is applied after service worker fetch event.
    sw_response2 = page.evaluate("() => window['fetchDummy']('foo')")
    assert sw_response2 == "responseFromServiceWorker:foo"

    # Page route is not applied to service worker initiated fetch.
    non_intercepted_response = page.evaluate(
        "() => window['fetchDummy']('passthrough')"
    )
    assert non_intercepted_response == "FAILURE: Not Found"

    # Firefox/Juggler does not want to fetch the redirect for some reason.
    if browser_name != "firefox":
        # Page route is not applied to service worker initiated fetch with redirect.
        server.set_redirect("/serviceworkers/fetchdummy/passthrough", "/simple.json")
        redirected_response = page.evaluate("() => window['fetchDummy']('passthrough')")
        assert redirected_response == '{"foo": "bar"}\n'


@pytest.mark.xfail(
    reason="python: url_matches does not normalize a literal glob like new URL() does (default ports, percent-encoding, IDN hosts)",
    strict=True,
)
def test_RO_153_should_work_with_glob() -> None:
    def glob_to_regex(glob: str) -> Pattern[str]:
        return re.compile(glob_to_regex_pattern(glob))

    assert glob_to_regex("**/*.js").search("https://localhost:8080/foo.js")
    assert not glob_to_regex("**/*.css").search("https://localhost:8080/foo.js")
    assert not glob_to_regex("*.js").search("https://localhost:8080/foo.js")
    assert glob_to_regex("https://**/*.js").search("https://localhost:8080/foo.js")
    assert glob_to_regex("http://localhost:8080/simple/path.js").search(
        "http://localhost:8080/simple/path.js"
    )
    assert glob_to_regex("**/{a,b}.js").search("https://localhost:8080/a.js")
    assert glob_to_regex("**/{a,b}.js").search("https://localhost:8080/b.js")
    assert not glob_to_regex("**/{a,b}.js").search("https://localhost:8080/c.js")

    assert glob_to_regex("**/*.{png,jpg,jpeg}").search("https://localhost:8080/c.jpg")
    assert glob_to_regex("**/*.{png,jpg,jpeg}").search("https://localhost:8080/c.jpeg")
    assert glob_to_regex("**/*.{png,jpg,jpeg}").search("https://localhost:8080/c.png")
    assert not glob_to_regex("**/*.{png,jpg,jpeg}").search(
        "https://localhost:8080/c.css"
    )
    assert glob_to_regex("foo*").search("foo.js")
    assert not glob_to_regex("foo*").search("foo/bar.js")
    assert not glob_to_regex("http://localhost:3000/signin-oidc*").search(
        "http://localhost:3000/signin-oidc/foo"
    )
    assert glob_to_regex("http://localhost:3000/signin-oidc*").search(
        "http://localhost:3000/signin-oidcnice"
    )

    assert glob_to_regex("**/*.js").search("/foo.js")
    assert not glob_to_regex("asd/**.js").search("/foo.js")
    assert not glob_to_regex("**/*.js").search("bar_foo.js")

    # range [] is NOT supported
    assert glob_to_regex("**/api/v[0-9]").search("http://example.com/api/v[0-9]")
    assert not glob_to_regex("**/api/v[0-9]").search("http://example.com/api/version")

    # query params
    assert glob_to_regex("**/api\\?param").search("http://example.com/api?param")
    assert not glob_to_regex("**/api\\?param").search("http://example.com/api-param")
    assert glob_to_regex("**/three-columns/settings.html\\?**id=settings-**").search(
        "http://mydomain:8080/blah/blah/three-columns/settings.html?id=settings-e3c58efe-02e9-44b0-97ac-dd138100cf7c&blah"
    )

    assert glob_to_regex("\\?").pattern == r"^\?$"
    assert glob_to_regex("\\").pattern == r"^\\$"
    assert glob_to_regex("\\\\").pattern == r"^\\$"
    assert glob_to_regex("\\[").pattern == r"^\[$"
    assert glob_to_regex("[a-z]").pattern == r"^\[a-z\]$"
    assert (
        glob_to_regex("$^+.\\*()|\\?\\{\\}\\[\\]").pattern
        == r"^\$\^\+\.\*\(\)\|\?\{\}\[\]$"
    )

    assert url_matches(None, "http://playwright.dev/", "http://playwright.dev")
    assert url_matches(None, "http://playwright.dev/?a=b", "http://playwright.dev?a=b")
    assert url_matches(None, "http://playwright.dev/", "h*://playwright.dev")
    assert url_matches(
        None, "http://api.playwright.dev/?x=y", "http://*.playwright.dev?x=y"
    )
    assert url_matches(None, "http://playwright.dev/foo/bar", "**/foo/**")
    assert url_matches("http://playwright.dev", "http://playwright.dev/?x=y", "?x=y")
    assert url_matches(
        "http://playwright.dev/foo/", "http://playwright.dev/foo/bar?x=y", "./bar?x=y"
    )

    # '$$', '$&', '$`' and "$'" are special in String.prototype.replace with a string argument.
    assert url_matches(
        None, "http://playwright.dev/foo$$bar", "http://playwright.dev/foo$$bar"
    )
    assert url_matches(None, "http://playwright.dev/a$&b", "http://playwright.dev/a$&b")
    assert url_matches("http://playwright.dev", "http://playwright.dev/p$$q", "./p$$q")

    # Case insensitive matching
    assert url_matches(
        None, "https://playwright.dev/fooBAR", "HtTpS://pLaYwRiGhT.dEv/fooBAR"
    )
    assert url_matches(
        "http://ignored",
        "https://playwright.dev/fooBAR",
        "HtTpS://pLaYwRiGhT.dEv/fooBAR",
    )
    # Path and search query are case-sensitive
    assert not url_matches(
        None, "https://playwright.dev/foobar", "https://playwright.dev/fooBAR"
    )
    assert not url_matches(
        None, "https://playwright.dev/foobar?a=b", "https://playwright.dev/foobar?A=B"
    )

    # Literal globs are normalized through new URL(), so explicit default ports,
    # percent-encoding and IDN hosts match request.url() which is already normalized.
    assert url_matches(None, "http://example.com/path", "http://example.com:80/path")
    assert url_matches(None, "https://example.com/path", "https://example.com:443/path")
    assert url_matches(
        None, "http://example.com:8080/path", "http://example.com:8080/path"
    )
    assert url_matches(None, "http://localhost/", "http://localhost:80/**")
    assert url_matches(
        None, "http://example.com/foo%20bar", "http://example.com/foo bar"
    )
    assert url_matches(None, "http://xn--mnchen-3ya.de/", "http://münchen.de/")

    assert url_matches(None, "https://localhost:3000/?a=b", "**/?a=b")
    assert url_matches(None, "https://localhost:3000/?a=b", "**?a=b")
    assert url_matches(None, "https://localhost:3000/?a=b", "**=b")

    # Custom schema.
    assert url_matches(None, "my.custom.protocol://foo", "my.custom.protocol://**")
    assert not url_matches(None, "my.p://foo", "my.{p,y}://**")
    assert url_matches(None, "my.p://foo/", "my.{p,y}://**")
    assert url_matches(None, "file:///foo/", "f*e://**")

    # This is not supported, we treat ? as a query separator.
    assert not glob_to_regex("http://localhost:8080/?imple/path.js").search(
        "http://localhost:8080/Simple/path.js"
    )
    assert not url_matches(None, "http://playwright.dev/", "http://playwright.?ev")
    assert url_matches(None, "http://playwright./?ev", "http://playwright.?ev")
    assert not url_matches(
        None, "http://playwright.dev/foo", "http://playwright.dev/f??"
    )
    assert url_matches(None, "http://playwright.dev/f??", "http://playwright.dev/f??")
    assert url_matches(
        None, "http://playwright.dev/?x=y", "http://playwright.dev\\?x=y"
    )
    assert url_matches(
        None, "http://playwright.dev/?x=y", "http://playwright.dev/\\?x=y"
    )
    assert url_matches(
        "http://playwright.dev/foo", "http://playwright.dev/foo?bar", "?bar"
    )
    assert url_matches(
        "http://playwright.dev/foo", "http://playwright.dev/foo?bar", "\\\\?bar"
    )
    assert url_matches("http://first.host/", "http://second.host/foo", "**/foo")
    assert url_matches("http://playwright.dev/", "http://localhost/", "*//localhost/")

    # /**/ should match /.
    assert url_matches(None, "https://foo/bar.js", "https://foo/**/bar.js")
    assert url_matches(None, "https://foo/bar.js", "https://foo/**/**/bar.js")

    custom_prefixes = ["about", "data", "chrome", "edge", "file"]
    for prefix in custom_prefixes:
        assert url_matches(
            "http://playwright.dev/", f"{prefix}:blank", f"{prefix}:blank"
        )
        assert not url_matches(
            "http://playwright.dev/", f"{prefix}:blank", "http://playwright.dev/"
        )
        assert url_matches(None, f"{prefix}:blank", f"{prefix}:blank")
        assert url_matches(None, f"{prefix}:blank", f"{prefix}:*")
        assert not url_matches(None, f"not{prefix}:blank", f"{prefix}:*")


@pytest.mark.xfail(
    reason="python: glob_to_regex_pattern does not raise on unbalanced or nested glob braces",
    strict=True,
)
def test_RO_154_should_throw_on_unbalanced_glob_braces() -> None:
    with pytest.raises(
        Exception, match=re.escape("Invalid glob pattern \"{foo\": unmatched '{'")
    ):
        glob_to_regex_pattern("{foo")
    with pytest.raises(
        Exception, match=re.escape("Invalid glob pattern \"}foo\": unmatched '}'")
    ):
        glob_to_regex_pattern("}foo")
    with pytest.raises(Exception, match="unmatched '{'"):
        glob_to_regex_pattern("http://*/foo{")
    with pytest.raises(Exception, match="unmatched '{'"):
        glob_to_regex_pattern("**/*.png?{")
    with pytest.raises(Exception, match="unmatched '{'"):
        glob_to_regex_pattern("https://example.com/{a")
    with pytest.raises(Exception, match="nested '{' is not supported"):
        glob_to_regex_pattern("{{foo}")
    # Escaped braces remain literal and must not throw.
    glob_to_regex_pattern("\\{foo")
    glob_to_regex_pattern("foo\\}")


@pytest.mark.xfail(
    reason="python: page.route() accepts a glob with an unmatched '{' and does not raise",
    strict=True,
)
def test_RO_155_should_throw_on_page_route_with_invalid_glob(page: Page) -> None:
    with pytest.raises(Error) as exc_info:
        page.route("http://*/foo{", lambda route: route.continue_())
    assert "unmatched '{'" in exc_info.value.message


def test_RO_156_should_intercept_by_glob(page: Page, server: Server) -> None:
    page.goto(server.EMPTY_PAGE)
    page.route(
        "http://localhos**?*oo",
        lambda route: route.fulfill(status=200, body="intercepted"),
    )
    result = page.evaluate(
        "url => fetch(url).then(r => r.text())", server.PREFIX + "/?foo"
    )
    assert result == "intercepted"


def fulfill_intercepted(route: Route) -> None:
    try:
        route.fulfill(status=200, body="intercepted")
    except Error:
        pass


def test_RO_157_should_intercept_network_activity_from_worker(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    server.set_route("/data_for_worker", end("failed to intercept"))
    url = server.PREFIX + "/data_for_worker"
    page.route(url, fulfill_intercepted)
    with page.expect_event("console") as msg_info:
        page.evaluate(
            """url => new Worker(URL.createObjectURL(new Blob([`
      fetch("${url}").then(response => response.text()).then(console.log);
    `], { type: 'application/javascript' })))""",
            url,
        )
    msg = msg_info.value
    assert msg.text == "intercepted"


def test_RO_158_should_intercept_worker_requests_when_enabled_after_worker_creation(
    page: Page, server: Server, browser_name: str, browser_major_version: int
) -> None:
    # https://github.com/microsoft/playwright/issues/32355
    if browser_name == "chromium" and browser_major_version < 130:
        pytest.skip("fixed in Chromium 130")

    page.goto(server.EMPTY_PAGE)
    server.set_route("/data_for_worker", end("failed to intercept"))
    url = server.PREFIX + "/data_for_worker"
    with page.expect_event("worker"):
        page.evaluate(
            """url => {
      window.w = new Worker(URL.createObjectURL(new Blob([`
        onmessage = function(e) {
          fetch("${url}").then(response => response.text()).then(console.log);
        };
      `], { type: 'application/javascript' })));
    }""",
            url,
        )
    # Install the route **after** the worker has been created.
    page.route(url, fulfill_intercepted)
    with page.expect_event("console") as msg_info:
        page.evaluate("() => window.w.postMessage('')")
    msg = msg_info.value
    assert msg.text == "intercepted"


def test_RO_159_should_intercept_network_activity_from_worker_2(
    page: Page, server: Server
) -> None:
    # https://github.com/microsoft/playwright/issues/31747
    url = server.PREFIX + "/worker/worker.js"

    def handler(route: Route) -> None:
        try:
            route.fulfill(
                status=200,
                body='console.log("intercepted");',
                content_type="application/javascript",
            )
        except Error:
            pass

    page.route(url, handler)
    with page.expect_event("console") as msg_info:
        page.goto(server.PREFIX + "/worker/worker.html")
    msg = msg_info.value
    assert msg.text == "intercepted"


def test_RO_162_should_not_break_remote_worker_import_scripts(
    page: Page, server: Server
) -> None:
    page.route("**", lambda route: route.continue_())
    page.goto(server.PREFIX + "/worker/worker-http-import.html")
    page.wait_for_selector("#status:has-text('finished')")


def test_RO_163_should_disable_memory_cache_when_intercepting(
    page: Page, server: Server
) -> None:
    interceted = 0

    def handler(route: Route) -> None:
        nonlocal interceted
        interceted += 1
        route.fulfill(body="success")

    page.route("**/page.html", handler)
    page.goto(server.PREFIX + "/page.html")
    assert "success" in (page.locator("body").text_content() or "")
    page.goto(server.EMPTY_PAGE)
    expect(page).to_have_url(server.EMPTY_PAGE)
    assert interceted == 1
    page.go_back()
    expect(page).to_have_url(server.PREFIX + "/page.html")
    assert interceted == 2


def test_RO_164_should_intercept_blob_url_requests(
    page: Page, server: Server, browser_name: str
) -> None:
    if browser_name != "webkit":
        pytest.skip("webkit only")
    page.goto(server.EMPTY_PAGE)
    page.route("**/*", fulfill_intercepted)
    page.on("console", lambda msg: print(msg.text))
    response = page.evaluate(
        """async () => {
    const blobUrl = URL.createObjectURL(new Blob(['failed to intercept'], { type: 'text/plain' }));
    return await fetch(blobUrl).then(response => response.text());
  }"""
    )
    assert response == "intercepted"
