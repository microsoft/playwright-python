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

"""Port of tests/library/browsercontext-base-url.spec.ts."""

from pathlib import Path
from typing import Callable, Dict

from playwright.async_api import Browser, BrowserType
from tests.server import Server
from tests.utils import must


async def test_NA_089_should_construct_a_new_url_when_a_base_url_in_browser_new_context_is_passed_to_page_goto_smoke(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(base_url=server.PREFIX)
    page = await context.new_page()
    assert must(await page.goto("/empty.html")).url == server.EMPTY_PAGE
    await context.close()


async def test_NA_090_should_construct_a_new_url_when_a_base_url_in_browser_new_page_is_passed_to_page_goto(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX)
    assert must(await page.goto("/empty.html")).url == server.EMPTY_PAGE
    await page.close()


async def test_NA_091_should_construct_a_new_url_when_a_base_url_in_browser_type_launch_persistent_context_is_passed_to_page_goto(
    browser_type: BrowserType,
    server: Server,
    create_user_data_dir: Callable[[], Path],
    launch_arguments: Dict,
) -> None:
    user_data_dir = create_user_data_dir()
    context = await browser_type.launch_persistent_context(
        user_data_dir, **launch_arguments, base_url=server.PREFIX
    )
    page = await context.new_page()
    assert must(await page.goto("/empty.html")).url == server.EMPTY_PAGE
    await context.close()


async def test_NA_092_should_construct_the_ur_ls_correctly_when_a_base_url_without_a_trailing_slash_in_browser_new_page_is_passed_to_page_goto(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX + "/url-construction")
    assert must(await page.goto("mypage.html")).url == server.PREFIX + "/mypage.html"
    assert must(await page.goto("./mypage.html")).url == server.PREFIX + "/mypage.html"
    assert must(await page.goto("/mypage.html")).url == server.PREFIX + "/mypage.html"
    await page.close()


async def test_NA_093_should_construct_the_ur_ls_correctly_when_a_base_url_with_a_trailing_slash_in_browser_new_page_is_passed_to_page_goto(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX + "/url-construction/")
    assert (
        must(await page.goto("mypage.html")).url
        == server.PREFIX + "/url-construction/mypage.html"
    )
    assert (
        must(await page.goto("./mypage.html")).url
        == server.PREFIX + "/url-construction/mypage.html"
    )
    assert must(await page.goto("/mypage.html")).url == server.PREFIX + "/mypage.html"
    assert must(await page.goto(".")).url == server.PREFIX + "/url-construction/"
    assert must(await page.goto("/")).url == server.PREFIX + "/"
    await page.close()


async def test_NA_094_should_not_construct_a_new_url_when_valid_ur_ls_are_passed(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url="http://microsoft.com")
    assert must(await page.goto(server.EMPTY_PAGE)).url == server.EMPTY_PAGE

    await page.goto("data:text/html,Hello world")
    assert (
        await page.evaluate("() => window.location.href")
        == "data:text/html,Hello world"
    )

    await page.goto("about:blank")
    assert await page.evaluate("() => window.location.href") == "about:blank"
    await page.close()


async def test_NA_095_should_be_able_to_match_a_url_relative_to_its_given_url_with_url_matcher(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX + "/foobar/")
    await page.goto("/kek/index.html")
    await page.wait_for_url("/kek/index.html")
    assert page.url == server.PREFIX + "/kek/index.html"

    await page.route(
        "./kek/index.html",
        lambda route: route.fulfill(body="base-url-matched-route"),
    )
    async with page.expect_request("./kek/index.html") as request_info:
        async with page.expect_response("./kek/index.html") as response_info:
            await page.goto("./kek/index.html")
    request = await request_info.value
    response = await response_info.value
    assert request.url == server.PREFIX + "/foobar/kek/index.html"
    assert response.url == server.PREFIX + "/foobar/kek/index.html"
    assert (await response.body()).decode() == "base-url-matched-route"
    await page.close()


async def test_NA_096_should_not_construct_a_new_url_with_base_url_when_a_glob_was_used(
    browser: Browser, server: Server
) -> None:
    page = await browser.new_page(base_url=server.PREFIX + "/foobar/")
    await page.goto("./kek/index.html")
    await page.wait_for_url("**/foobar/kek/index.html")
    await page.close()
