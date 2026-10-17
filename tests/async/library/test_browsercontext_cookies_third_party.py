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

"""Port of tests/library/browsercontext-cookies-third-party.spec.ts."""

import json
from pathlib import Path
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    cast,
)
from urllib.parse import urlparse

import pytest

from playwright.async_api import BrowserContext, BrowserType, Page, expect
from tests.server import Server, TestServerRequest
from tests.utils import provisional_xfail

# Upstream: test.use({ ignoreHTTPSErrors: true }). It applies to every context that the
# tests create, so each new_context() and launch_persistent() below passes it too.
CONTEXT_OPTIONS: Dict[str, Any] = {"ignore_https_errors": True}


@pytest.fixture
async def context(
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> AsyncGenerator[BrowserContext, None]:
    context = await context_factory(**CONTEXT_OPTIONS)
    yield context
    await context.close()


@pytest.fixture
async def own_browser_context_factory(
    browser_name: str,
    browser_type: BrowserType,
    launch_arguments: Dict,
    context_factory: Callable[..., Awaitable[BrowserContext]],
) -> AsyncGenerator[Callable[..., Awaitable[BrowserContext]], None]:
    """Creates the contexts of a test in a browser of their own, on Firefox.

    In Firefox, a 'Partitioned' cookie that a top-level page sets reaches a third-party
    frame only in the first context of the browser; in the later contexts, it does not.
    The upstream expectations are those of the first context, so the tests that check it
    run in a new browser. Elsewhere, this is context_factory.
    """
    if browser_name != "firefox":
        yield context_factory
        return
    browser = await browser_type.launch(**launch_arguments)
    yield lambda **options: browser.new_context(**options)
    await browser.close()


@pytest.fixture
def urls(https_server: Server) -> Dict[str, str]:
    origin1 = https_server.PREFIX
    origin2 = https_server.CROSS_PROCESS_PREFIX
    return {
        "origin1": origin1,
        "origin2": origin2,
        "read_origin1": origin1 + "/read-cookie.html",
        "read_origin2_origin1": origin2 + "/frame-read-cookie.html",
        "read_origin1_origin1": origin1 + "/frame-read-cookie.html",
        "read_origin1_origin2_origin1": origin1 + "/nested-frame-read-cookie.html",
        "set_origin1": origin1 + "/set-cookie.html",
        "set_origin2_origin1": origin2 + "/frame-set-cookie.html",
        "set_origin1_origin2_origin1": origin1 + "/nested-frame-set-cookie.html",
    }


@pytest.fixture
def webkit_partitions(browser_name: str, is_mac: bool, mac_version: int) -> bool:
    return browser_name == "webkit" and is_mac and mac_version >= 26


def html_handler(body: str) -> Callable[[TestServerRequest], None]:
    def handler(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.write(body.encode())
        request.finish()

    return handler


def add_common_cookie_handlers(https_server: Server, urls: Dict[str, str]) -> None:
    """Port of addCommonCookieHandlers().

    origin1:
      top-level-partitioned=value
      top-level-non-partitioned=value

    origin2:
      origin1:
        frame-partitioned=value
        frame-non-partitioned=value

    origin1:
      origin2:
        origin1:
          frame-partitioned=value
          frame-non-partitioned=value

    origin1 = https_server.PREFIX
    origin2 = https_server.CROSS_PROCESS_PREFIX
    """

    # '/set-cookie.html' handlers are added in the tests.
    def read_cookie(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        header = request.getHeader("cookie")
        cookies = (
            "; ".join(sorted(c.strip() for c in header.split(";")))
            if header is not None
            else "undefined"
        )
        request.write(f"Received cookie: {cookies}".encode())
        request.finish()

    https_server.set_route("/read-cookie.html", read_cookie)
    https_server.set_route(
        "/frame-set-cookie.html",
        html_handler(f"<iframe src='{urls['origin1']}/set-cookie.html'></iframe>"),
    )
    https_server.set_route(
        "/frame-read-cookie.html",
        html_handler(f"<iframe src='{urls['origin1']}/read-cookie.html'></iframe>"),
    )
    # Nested cross-origin iframe:
    #   main frame: (origin1 or origin2) -> iframe1: origin2 -> iframe2: origin1
    https_server.set_route(
        "/nested-frame-set-cookie.html",
        html_handler(
            f"<iframe src='{urls['origin2']}/frame-set-cookie.html'></iframe>"
        ),
    )
    https_server.set_route(
        "/nested-frame-read-cookie.html",
        html_handler(
            f"<iframe src='{urls['origin2']}/frame-read-cookie.html'></iframe>"
        ),
    )


def set_cookie_handler(
    cookies: Callable[[str], List[str]],
) -> Callable[[TestServerRequest], None]:
    """Answers with the Set-Cookie headers for "frame" or "top-level" (no referer)."""

    def handler(request: TestServerRequest) -> None:
        prefix = "frame" if request.getHeader("referer") else "top-level"
        request.responseHeaders.setRawHeaders("Set-Cookie", cookies(prefix))
        request.finish()

    return handler


def find_cookie(cookies: Sequence[Any], name: str) -> Dict[str, Any]:
    result = next((cookie for cookie in cookies if cookie["name"] == name), None)
    assert result, f"Cookie {name} not found in {json.dumps(cookies, indent=2)}"
    return dict(result)


def expect_partition_key(
    cookies: Sequence[Any], name: str, partition_key: Optional[str]
) -> None:
    cookie = find_cookie(cookies, name)
    if partition_key != cookie.get("partitionKey"):
        raise Exception(
            f"Cookie {name} has partitionKey {cookie.get('partitionKey')} "
            f"but expected {partition_key}."
        )


async def run_non_partitioned_test(
    page: Page,
    https_server: Server,
    browser_name: str,
    is_mac: bool,
    is_linux: bool,
    browser_channel: Optional[str],
    urls: Dict[str, str],
) -> Tuple[str, str]:
    add_common_cookie_handlers(https_server, urls)

    def handler(request: TestServerRequest) -> None:
        prefix = "frame" if request.getHeader("referer") else "top-level"
        request.setHeader(
            "Set-Cookie", f"{prefix}=value; SameSite=None; Path=/; Secure;"
        )
        request.setHeader("Content-Type", "text/html")
        request.finish()

    https_server.set_route("/set-cookie.html", handler)

    await page.goto(urls["set_origin1"])
    await page.goto(urls["read_origin1"])
    assert (
        await page.locator("body").text_content() == "Received cookie: top-level=value"
    )

    await page.goto(urls["read_origin2_origin1"])
    frame_body = page.locator("iframe").content_frame.locator("body")

    # WebKit does not support third-party cookies without a 'Partition' attribute.
    if browser_name == "webkit" and is_mac:
        await expect(frame_body).to_have_text("Received cookie: undefined")
    else:
        await expect(frame_body).to_have_text("Received cookie: top-level=value")

    # Set cookie and do second navigation.
    await page.goto(urls["set_origin2_origin1"])
    await page.goto(urls["read_origin2_origin1"])
    expected_third_party = "Received cookie: "
    if browser_name == "webkit" and is_mac:
        expected_third_party += "undefined"
    elif browser_name == "webkit" and (is_linux or browser_channel == "webkit-wsl"):
        expected_third_party += "top-level=value"
    else:
        expected_third_party += "frame=value; top-level=value"
    await expect(frame_body).to_have_text(expected_third_party, timeout=1000)

    # Check again the top-level cookie.
    await page.goto(urls["read_origin1"])
    expected_top_level = (
        "Received cookie: top-level=value"
        if browser_name == "webkit"
        and (is_mac or is_linux or browser_channel == "webkit-wsl")
        else "Received cookie: frame=value; top-level=value"
    )
    assert await page.locator("body").text_content() == expected_top_level

    return expected_top_level, expected_third_party


async def test_CO_052_third_party_non_partitioned_cookies(
    page: Page,
    browser_name: str,
    https_server: Server,
    is_mac: bool,
    is_linux: bool,
    urls: Dict[str, str],
    browser_channel: Optional[str],
) -> None:
    await run_non_partitioned_test(
        page, https_server, browser_name, is_mac, is_linux, browser_channel, urls
    )


async def test_CO_053_save_load_third_party_non_partitioned_cookies(
    page: Page,
    browser_name: str,
    https_server: Server,
    is_mac: bool,
    is_linux: bool,
    context_factory: Callable[..., Awaitable[BrowserContext]],
    urls: Dict[str, str],
    browser_channel: Optional[str],
) -> None:
    # Run the test to populate the cookies.
    expected_top_level, expected_third_party = await run_non_partitioned_test(
        page, https_server, browser_name, is_mac, is_linux, browser_channel, urls
    )

    async def check_cookies(page: Page) -> None:
        # Check top-level cookie first.
        await page.goto(urls["read_origin1"])
        assert await page.locator("body").text_content() == expected_top_level

        # Check third-party cookie.
        await page.goto(urls["read_origin2_origin1"])
        frame_body = page.locator("iframe").content_frame.locator("body")
        await expect(frame_body).to_have_text(expected_third_party)

    await check_cookies(page)

    # export via cookies/addCookies
    cookies = await page.context.cookies()
    context2 = await context_factory(**CONTEXT_OPTIONS)
    await context2.add_cookies(cast(Any, cookies))
    page2 = await context2.new_page()
    await check_cookies(page2)

    # export via storageState
    storage_state = await page.context.storage_state()
    context3 = await context_factory(**CONTEXT_OPTIONS, storage_state=storage_state)
    page3 = await context3.new_page()
    await check_cookies(page3)


async def run_partitioned_test(
    page: Page,
    https_server: Server,
    browser_name: str,
    is_mac: bool,
    webkit_partitions: bool,
    urls: Dict[str, str],
) -> None:
    add_common_cookie_handlers(https_server, urls)
    https_server.set_route(
        "/set-cookie.html",
        set_cookie_handler(
            lambda prefix: [
                f"{prefix}-partitioned=value; SameSite=None; Path=/; Secure; Partitioned;",
                f"{prefix}-non-partitioned=value; SameSite=None; Path=/; Secure;",
            ]
        ),
    )

    await page.goto(urls["set_origin1"])
    await page.goto(urls["read_origin1"])
    assert (
        await page.locator("body").text_content()
        == "Received cookie: top-level-non-partitioned=value; top-level-partitioned=value"
    )

    await page.goto(urls["read_origin2_origin1"])
    frame_body = page.locator("iframe").content_frame.locator("body")

    # Firefox cookie partitioning is disabled in Firefox(Juggler).
    # TODO: reenable cookie partitioning?
    if browser_name == "firefox":
        await expect(frame_body).to_have_text(
            "Received cookie: top-level-non-partitioned=value; top-level-partitioned=value"
        )
        return

    # Linux and Windows WebKit builds do not partition third-party cookies at all.
    if browser_name == "webkit" and not is_mac:
        await expect(frame_body).to_have_text(
            "Received cookie: top-level-non-partitioned=value; top-level-partitioned=value"
        )
        return

    if browser_name == "webkit":
        # WebKit will only send 'Partitioned' third-party cookies exactly matching the partition.
        await expect(frame_body).to_have_text("Received cookie: undefined")
    else:
        # For non-partitioned cookies, the cookie is sent to the iframe right away,
        # if third-party cookies are supported by the browser.
        await expect(frame_body).to_have_text(
            "Received cookie: top-level-non-partitioned=value"
        )

    # First navigation:
    # - no cookie sent, as it was only set on the top-level site
    # - sets the third-party cookie for the top-level context
    # Second navigation:
    # - sends the cookie as it was just set for the (top-level site, iframe url) partition.
    await page.goto(urls["set_origin2_origin1"])
    await page.goto(urls["read_origin2_origin1"])
    if browser_name == "webkit":
        await expect(frame_body).to_have_text(
            "Received cookie: frame-partitioned=value"
            if webkit_partitions
            else "Received cookie: undefined"
        )
    else:
        await expect(frame_body).to_have_text(
            "Received cookie: frame-non-partitioned=value; frame-partitioned=value; "
            "top-level-non-partitioned=value"
        )


async def test_CO_054_third_party_partitioned_cookies(
    own_browser_context_factory: Callable[..., Awaitable[BrowserContext]],
    browser_name: str,
    https_server: Server,
    is_mac: bool,
    webkit_partitions: bool,
    urls: Dict[str, str],
) -> None:
    context = await own_browser_context_factory(**CONTEXT_OPTIONS)
    page = await context.new_page()
    await run_partitioned_test(
        page, https_server, browser_name, is_mac, webkit_partitions, urls
    )


async def test_CO_055_save_load_third_party_partitioned_cookies(
    page: Page,
    browser_name: str,
    https_server: Server,
    is_mac: bool,
    webkit_partitions: bool,
    context_factory: Callable[..., Awaitable[BrowserContext]],
    urls: Dict[str, str],
) -> None:
    if browser_name == "firefox":
        pytest.skip(
            "fixme: Firefox cookie partitioning is disabled in Firefox(Juggler)."
        )
    if browser_name == "webkit" and not is_mac:
        pytest.skip(
            "fixme: Linux and Windows WebKit builds do not partition third-party "
            "cookies at all."
        )

    await run_partitioned_test(
        page, https_server, browser_name, is_mac, webkit_partitions, urls
    )

    async def check_cookies(page: Page) -> None:
        # Check top-level cookie first.
        await page.goto(urls["read_origin1"])
        expected_top_level = (
            "Received cookie: top-level-non-partitioned=value; "
            "top-level-partitioned=value"
            if browser_name == "webkit" and is_mac
            else "Received cookie: frame-non-partitioned=value; "
            "top-level-non-partitioned=value; top-level-partitioned=value"
        )
        assert await page.locator("body").text_content() == expected_top_level

        # Check third-party cookie.
        await page.goto(urls["read_origin2_origin1"])
        frame_body = page.locator("iframe").content_frame.locator("body")
        expected_third_party = (
            (
                "Received cookie: frame-partitioned=value"
                if webkit_partitions
                else "Received cookie: undefined"
            )
            if browser_name == "webkit"
            else "Received cookie: frame-non-partitioned=value; "
            "frame-partitioned=value; top-level-non-partitioned=value"
        )
        await expect(frame_body).to_have_text(expected_third_party, timeout=1000)

        # read-origin1-origin2-origin1.html
        await page.goto(urls["read_origin1_origin2_origin1"])
        frame_body = (
            page.locator("iframe")
            .content_frame.locator("iframe")
            .content_frame.locator("body")
        )
        expected_third_party = (
            "Received cookie: top-level-non-partitioned=value; "
            "top-level-partitioned=value"
            if browser_name == "webkit"
            else "Received cookie: frame-non-partitioned=value; "
            "top-level-non-partitioned=value"
        )
        await expect(frame_body).to_have_text(expected_third_party, timeout=1000)

    await check_cookies(page)

    def check_storage_cookies(cookies: Sequence[Any]) -> None:
        webkit_no_partition = browser_name == "webkit" and not webkit_partitions
        expect_partition_key(
            cookies,
            "top-level-partitioned",
            None if webkit_no_partition else "https://localhost",
        )
        expect_partition_key(cookies, "top-level-non-partitioned", None)
        if webkit_no_partition:
            assert not any(c["name"] == "frame-partitioned" for c in cookies)
            assert not any(c["name"] == "frame-non-partitioned" for c in cookies)
        else:
            expect_partition_key(cookies, "frame-partitioned", "https://127.0.0.1")
            if browser_name == "webkit":
                assert not any(c["name"] == "frame-non-partitioned" for c in cookies)
            else:
                expect_partition_key(cookies, "frame-non-partitioned", None)

    check_storage_cookies(await page.context.cookies())
    check_storage_cookies((await page.context.storage_state())["cookies"])

    # export via cookies/addCookies
    cookies = await page.context.cookies()
    context2 = await context_factory(**CONTEXT_OPTIONS)
    await context2.add_cookies(cast(Any, cookies))
    page2 = await context2.new_page()
    await check_cookies(page2)

    # export via storageState
    storage_state = await page.context.storage_state()
    context3 = await context_factory(**CONTEXT_OPTIONS, storage_state=storage_state)
    page3 = await context3.new_page()
    await check_cookies(page3)


async def test_CO_056_add_partitioned_cookie_via_api(
    page: Page,
    context: BrowserContext,
    browser_name: str,
    https_server: Server,
    is_mac: bool,
    webkit_partitions: bool,
    urls: Dict[str, str],
) -> None:
    add_common_cookie_handlers(https_server, urls)

    await context.add_cookies(
        cast(
            Any,
            [
                {
                    "name": "top-level-partitioned",
                    "value": "value",
                    "domain": https_server.HOSTNAME,
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None",
                    "partitionKey": "https://localhost",
                    "_crHasCrossSiteAncestor": False,
                },
                {
                    "name": "top-level-non-partitioned",
                    "value": "value",
                    "domain": https_server.HOSTNAME,
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None",
                },
                {
                    "name": "frame-partitioned",
                    "value": "value",
                    "domain": https_server.HOSTNAME,
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None",
                    "partitionKey": "https://127.0.0.1",
                    "_crHasCrossSiteAncestor": True,
                },
                {
                    "name": "frame-non-partitioned",
                    "value": "value",
                    "domain": https_server.HOSTNAME,
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None",
                },
            ],
        )
    )

    async def check_cookies(page: Page) -> None:
        # Check top-level cookie first.
        await page.goto(urls["read_origin1"])
        if browser_name == "webkit" and is_mac and not webkit_partitions:
            expected_top_level = (
                "Received cookie: frame-non-partitioned=value; "
                "top-level-non-partitioned=value"
            )
        elif (browser_name == "webkit" and not webkit_partitions) or (
            browser_name == "firefox"
        ):
            expected_top_level = (
                "Received cookie: frame-non-partitioned=value; "
                "frame-partitioned=value; top-level-non-partitioned=value; "
                "top-level-partitioned=value"
            )
        else:
            expected_top_level = (
                "Received cookie: frame-non-partitioned=value; "
                "top-level-non-partitioned=value; top-level-partitioned=value"
            )
        assert await page.locator("body").text_content() == expected_top_level

        # Check third-party cookie.
        await page.goto(urls["read_origin2_origin1"])
        frame_body = page.locator("iframe").content_frame.locator("body")
        expected_third_party = "Received cookie: "
        if webkit_partitions:
            expected_third_party += "frame-partitioned=value"
        elif browser_name == "webkit" and is_mac:
            expected_third_party += "undefined"
        elif browser_name == "chromium":
            expected_third_party += (
                "frame-non-partitioned=value; frame-partitioned=value; "
                "top-level-non-partitioned=value"
            )
        else:
            # Firefox(Juggler) and WebKit on Linux/Windows do not partition
            # third-party cookies.
            expected_third_party += (
                "frame-non-partitioned=value; frame-partitioned=value; "
                "top-level-non-partitioned=value; top-level-partitioned=value"
            )
        await expect(frame_body).to_have_text(expected_third_party, timeout=1000)

        # read-origin1-origin2-origin1.html
        await page.goto(urls["read_origin1_origin2_origin1"])
        frame_body = (
            page.locator("iframe")
            .content_frame.locator("iframe")
            .content_frame.locator("body")
        )
        expected_third_party = "Received cookie: "
        if webkit_partitions:
            expected_third_party += (
                "frame-non-partitioned=value; top-level-non-partitioned=value; "
                "top-level-partitioned=value"
            )
        elif browser_name == "webkit" and is_mac:
            expected_third_party += (
                "frame-non-partitioned=value; top-level-non-partitioned=value"
            )
        elif browser_name == "webkit" or browser_name == "firefox":
            expected_third_party += (
                "frame-non-partitioned=value; frame-partitioned=value; "
                "top-level-non-partitioned=value; top-level-partitioned=value"
            )
        else:
            expected_third_party += (
                "frame-non-partitioned=value; top-level-non-partitioned=value"
            )
        await expect(frame_body).to_have_text(expected_third_party, timeout=1000)

    await check_cookies(page)


async def test_CO_057_same_origin_third_party_partitioned_cookie_with_different_origin_intermediate_iframe(
    page: Page,
    https_server: Server,
    context_factory: Callable[..., Awaitable[BrowserContext]],
    urls: Dict[str, str],
) -> None:
    add_common_cookie_handlers(https_server, urls)
    https_server.set_route(
        "/set-cookie.html",
        set_cookie_handler(
            lambda prefix: [
                f"{prefix}-partitioned=value; SameSite=None; Path=/; Secure; Partitioned;",
                f"{prefix}-non-partitioned=value; SameSite=None; Path=/; Secure;",
            ]
        ),
    )
    # main frame: origin1 -> iframe1: origin2 -> iframe2: origin1
    # In this case the cookie in iframe2 is a third-party partitioned cookie, even though
    # it's the same origin as the main frame.
    await page.goto(urls["set_origin1_origin2_origin1"])

    async def check_cookies(page: Page) -> None:
        await page.goto(urls["read_origin1_origin2_origin1"])
        frame_body = (
            page.locator("iframe")
            .content_frame.locator("iframe")
            .content_frame.locator("body")
        )
        await expect(frame_body).to_have_text(
            "Received cookie: frame-non-partitioned=value; frame-partitioned=value"
        )

    await check_cookies(page)

    # export via cookies/addCookies
    cookies = await page.context.cookies()
    context2 = await context_factory(**CONTEXT_OPTIONS)
    await context2.add_cookies(cast(Any, cookies))
    page2 = await context2.new_page()
    await check_cookies(page2)

    # export via storageState
    storage_state = await page.context.storage_state()
    context3 = await context_factory(**CONTEXT_OPTIONS, storage_state=storage_state)
    page3 = await context3.new_page()
    await check_cookies(page3)


async def test_CO_058_top_level_partitioned_cookie_and_same_origin_iframe(
    own_browser_context_factory: Callable[..., Awaitable[BrowserContext]],
    browser_name: str,
    https_server: Server,
    urls: Dict[str, str],
    tmp_path: Path,
    platform: str,
    request: pytest.FixtureRequest,
) -> None:
    if browser_name == "firefox" and platform == "darwin":
        # Failed on the macos-latest runner of CI only (the third-party frame did not
        # get the partitioned cookie), and passed there in the run before.
        provisional_xfail(request, "flaky on the macOS Firefox runners of CI")
    context_factory = own_browser_context_factory
    context = await context_factory(**CONTEXT_OPTIONS)
    page = await context.new_page()
    add_common_cookie_handlers(https_server, urls)
    https_server.set_route(
        "/set-cookie.html",
        set_cookie_handler(
            lambda prefix: [
                f"{prefix}=value; SameSite=None; Path=/; Secure; Partitioned;",
                f"{prefix}-non-partitioned=value; SameSite=None; Path=/; Secure;",
            ]
        ),
    )

    # Same origin iframe cookies are partitioned the same way as top-level cookies.
    await page.goto(urls["set_origin1"])
    await page.context.storage_state(path=tmp_path / "state2.json")

    async def check_cookies(page: Page) -> None:
        # Check top-level cookie first.
        await page.goto(urls["read_origin1"])
        assert (
            await page.locator("body").text_content()
            == "Received cookie: top-level-non-partitioned=value; top-level=value"
        )

        # Same origin iframe.
        await page.goto(urls["read_origin1_origin1"])
        frame_body = page.locator("iframe").content_frame.locator("body")
        await expect(frame_body).to_have_text(
            "Received cookie: top-level-non-partitioned=value; top-level=value",
            timeout=1000,
        )

        # Check third-party cookie.
        # main frame: origin1 -> iframe1: origin2 -> iframe2: origin1
        await page.goto(urls["read_origin1_origin2_origin1"])
        frame_body = (
            page.locator("iframe")
            .content_frame.locator("iframe")
            .content_frame.locator("body")
        )
        expected_third_party = "Received cookie: "
        if browser_name == "chromium":
            expected_third_party += "top-level-non-partitioned=value"
        else:
            expected_third_party += "top-level-non-partitioned=value; top-level=value"
        await expect(frame_body).to_have_text(expected_third_party, timeout=1000)

    await check_cookies(page)

    # export via cookies/addCookies
    cookies = await page.context.cookies()
    context2 = await context_factory(**CONTEXT_OPTIONS)
    await context2.add_cookies(cast(Any, cookies))
    page2 = await context2.new_page()
    await check_cookies(page2)

    # export via storageState
    storage_state = await page.context.storage_state()
    context3 = await context_factory(**CONTEXT_OPTIONS, storage_state=storage_state)
    page3 = await context3.new_page()
    await check_cookies(page3)


async def test_CO_059_should_be_able_to_send_third_party_cookies_via_an_iframe(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    https_server: Server,
    browser_name: str,
    is_mac: bool,
) -> None:
    if browser_name == "webkit" and is_mac:
        pytest.skip("fixme: webkit on mac")

    context = await context_factory(ignore_https_errors=True)
    try:
        page = await context.new_page()
        await page.goto(https_server.EMPTY_PAGE)
        await context.add_cookies(
            [
                {
                    "domain": urlparse(https_server.CROSS_PROCESS_PREFIX).hostname,
                    "path": "/",
                    "name": "cookie1",
                    "value": "yes",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None",
                }
            ]
        )
        with https_server.expect_request("/grid.html") as request_info:
            await page.set_content(
                f'<iframe src="{https_server.CROSS_PROCESS_PREFIX}/grid.html"></iframe>'
            )
        assert request_info.value.getHeader("cookie") == "cookie1=yes"
    finally:
        await context.close()


async def check_third_party_cookies_are_blocked(
    page: Page,
    context: BrowserContext,
    server: Server,
    allows_third_party: bool,
    default_same_site_cookie_value: str,
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """src => {
            let fulfill;
            const promise = new Promise(x => fulfill = x);
            const iframe = document.createElement('iframe');
            document.body.appendChild(iframe);
            iframe.onload = fulfill;
            iframe.src = src;
            return promise;
        }""",
        server.CROSS_PROCESS_PREFIX + "/grid.html",
    )
    document_cookie = await page.frames[1].evaluate(
        """() => {
            document.cookie = 'username=John Doe';
            return document.cookie;
        }"""
    )
    await page.wait_for_timeout(2000)
    assert document_cookie == ("username=John Doe" if allows_third_party else "")
    cookies = await context.cookies(server.CROSS_PROCESS_PREFIX + "/grid.html")
    if allows_third_party:
        assert cookies == [
            {
                "domain": "127.0.0.1",
                "expires": -1,
                "httpOnly": False,
                "name": "username",
                "path": "/",
                "sameSite": default_same_site_cookie_value,
                "secure": False,
                "value": "John Doe",
            }
        ]
    else:
        assert cookies == []


async def test_CO_060_should_not_block_third_party_cookies_persistent_context(
    https_server: Server,
    launch_persistent: Callable[..., Awaitable[Tuple[BrowserContext, Page]]],
    allows_third_party: bool,
    default_same_site_cookie_value: str,
) -> None:
    context, page = await launch_persistent(**CONTEXT_OPTIONS)
    await check_third_party_cookies_are_blocked(
        page, context, https_server, allows_third_party, default_same_site_cookie_value
    )


async def test_CO_061_should_not_block_third_party_cookies_ephemeral_context(
    page: Page,
    context: BrowserContext,
    https_server: Server,
    allows_third_party: bool,
    default_same_site_cookie_value: str,
) -> None:
    await check_third_party_cookies_are_blocked(
        page, context, https_server, allows_third_party, default_same_site_cookie_value
    )


async def test_CO_062_should_not_block_third_party_same_site_none_cookies(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    https_server: Server,
    browser_name: str,
) -> None:
    if browser_name == "webkit":
        pytest.skip("No third party cookies in WebKit")
    context = await context_factory(ignore_https_errors=True)
    page = await context.new_page()

    https_server.set_route(
        "/empty.html",
        html_handler(
            f'<iframe src="{https_server.CROSS_PROCESS_PREFIX}/grid.html"></iframe>'
        ),
    )

    def grid(request: TestServerRequest) -> None:
        request.setResponseCode(200)
        request.setHeader(
            "Set-Cookie", "a=b; Path=/; Max-Age=3600; SameSite=None; Secure"
        )
        request.setHeader("Content-Type", "text/html")
        request.write(
            b"""Hello world
    <script>
    setTimeout(() => fetch('/json'), 1000);
    </script>"""
        )
        request.finish()

    https_server.set_route("/grid.html", grid)

    cookie: List[Optional[str]] = []

    def json_handler(request: TestServerRequest) -> None:
        cookie.append(request.getHeader("cookie"))
        request.finish()

    https_server.set_route("/json", json_handler)

    # The /json request comes from a timer in the iframe: wait for its response.
    async with page.expect_response("**/json"):
        await page.goto(https_server.EMPTY_PAGE)
    assert cookie == ["a=b"]
