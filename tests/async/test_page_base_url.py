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

from playwright.async_api import Browser, BrowserType
from tests.server import Server


async def test_should_construct_a_new_url_when_a_base_url_in_browser_new_context_is_passed(
    browser: Browser, server: Server
):
    context = await browser.new_context(base_url=server.PREFIX)
    page = await context.new_page()
    assert (await page.goto("/empty.html")).url == server.EMPTY_PAGE
    await context.close()


async def test_should_construct_a_new_url_when_a_base_url_in_browser_new_page_is_passed(
    browser: Browser, server: Server
):
    page = await browser.new_page(base_url=server.PREFIX)
    assert (await page.goto("/empty.html")).url == server.EMPTY_PAGE
    await page.close()


async def test_should_construct_a_new_url_when_a_base_url_in_browser_new_persistent_context_is_passed(
    browser_type: BrowserType, tmpdir, server: Server, launch_arguments
):
    context = await browser_type.launch_persistent_context(
        tmpdir, **launch_arguments, base_url=server.PREFIX
    )
    page = await context.new_page()
    assert (await page.goto("/empty.html")).url == server.EMPTY_PAGE
    await context.close()


async def test_should_construct_correctly_when_a_baseurl_without_a_trailing_slash_is_passed(
    browser: Browser, server: Server
):
    page = await browser.new_page(base_url=server.PREFIX + "/url-construction")
    assert (await page.goto("mypage.html")).url == server.PREFIX + "/mypage.html"
    assert (await page.goto("./mypage.html")).url == server.PREFIX + "/mypage.html"
    assert (await page.goto("/mypage.html")).url == server.PREFIX + "/mypage.html"
    await page.close()


async def test_should_construct_correctly_when_a_baseurl_with_a_trailing_slash_is_passed(
    browser: Browser, server: Server
):
    page = await browser.new_page(base_url=server.PREFIX + "/url-construction/")
    assert (
        await page.goto("mypage.html")
    ).url == server.PREFIX + "/url-construction/mypage.html"
    assert (
        await page.goto("./mypage.html")
    ).url == server.PREFIX + "/url-construction/mypage.html"
    assert (await page.goto("/mypage.html")).url == server.PREFIX + "/mypage.html"
    assert (await page.goto(".")).url == server.PREFIX + "/url-construction/"
    assert (await page.goto("/")).url == server.PREFIX + "/"
    await page.close()


async def test_should_not_construct_a_new_url_when_valid_urls_are_passed(
    browser: Browser, server: Server
):
    page = await browser.new_page(base_url="http://microsoft.com")
    assert (await page.goto(server.EMPTY_PAGE)).url == server.EMPTY_PAGE

    await page.goto("data:text/html,Hello world")
    assert page.url == "data:text/html,Hello world"

    await page.goto("about:blank")
    assert page.url == "about:blank"

    await page.close()


async def test_should_be_able_to_match_a_url_relative_to_its_given_url_with_urlmatcher(
    browser: Browser, server: Server
):
    page = await browser.new_page(base_url=server.PREFIX + "/foobar/")

    await page.goto("/kek/index.html")
    await page.wait_for_url("/kek/index.html")
    assert page.url == server.PREFIX + "/kek/index.html"

    await page.route(
        "./kek/index.html", lambda route: route.fulfill(body="base-url-matched-route")
    )

    async with page.expect_request("./kek/index.html") as request_info:
        async with page.expect_response("./kek/index.html") as response_info:
            await page.goto("./kek/index.html")
    request = await request_info.value
    response = await response_info.value
    assert request.url == server.PREFIX + "/foobar/kek/index.html"
    assert response.url == server.PREFIX + "/foobar/kek/index.html"
    assert await response.body() == b"base-url-matched-route"

    await page.close()
