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
import os
import pathlib
import sys

import pytest

from playwright import Error
from playwright.helper import TimeoutError
from playwright.network import Request

__dirname = os.path.dirname(os.path.realpath(__file__))


async def test_goto_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE


async def test_goto_should_work_with_file_URL(page, server):
    fileurl = pathlib.Path(
        os.path.join(__dirname, "assets", "frames", "two-frames.html")
    ).as_uri()
    await page.goto(fileurl)
    assert page.url.lower() == fileurl.lower()
    assert len(page.frames) == 3


async def test_goto_should_use_http_for_no_protocol(page, server):
    await page.goto(server.EMPTY_PAGE[7:])
    assert page.url == server.EMPTY_PAGE


async def test_goto_should_work_cross_process(page, server):
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE

    url = server.CROSS_PROCESS_PREFIX + "/empty.html"
    request_frames = []

    def on_request(r: Request) -> None:
        if r.url == url:
            request_frames.append(r.frame)

    page.on("request", on_request)

    response = await page.goto(url)
    assert page.url == url
    assert response.frame == page.mainFrame
    assert request_frames[0] == page.mainFrame
    assert response.url == url


async def test_goto_should_capture_iframe_navigation_request(page, server):
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE

    request_frames = []

    def on_request(r: Request) -> None:
        if r.url == server.PREFIX + "/frames/frame.html":
            request_frames.append(r.frame)

    page.on("request", on_request)

    response = await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert page.url == server.PREFIX + "/frames/one-frame.html"
    assert response.frame == page.mainFrame
    assert response.url == server.PREFIX + "/frames/one-frame.html"

    assert len(page.frames) == 2
    assert request_frames[0] == page.frames[1]


async def test_goto_should_capture_cross_process_iframe_navigation_request(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE

    request_frames = []

    def on_request(r: Request) -> None:
        if r.url == server.CROSS_PROCESS_PREFIX + "/frames/frame.html":
            request_frames.append(r.frame)

    page.on("request", on_request)

    response = await page.goto(server.CROSS_PROCESS_PREFIX + "/frames/one-frame.html")
    assert page.url == server.CROSS_PROCESS_PREFIX + "/frames/one-frame.html"
    assert response.frame == page.mainFrame
    assert response.url == server.CROSS_PROCESS_PREFIX + "/frames/one-frame.html"

    assert len(page.frames) == 2
    assert request_frames[0] == page.frames[1]


async def test_goto_should_work_with_anchor_navigation(page, server):
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE
    await page.goto(server.EMPTY_PAGE + "#foo")
    assert page.url == server.EMPTY_PAGE + "#foo"
    await page.goto(server.EMPTY_PAGE + "#bar")
    assert page.url == server.EMPTY_PAGE + "#bar"


async def test_goto_should_work_with_redirects(page, server):
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/empty.html")
    response = await page.goto(server.PREFIX + "/redirect/1.html")
    assert response.status == 200
    assert page.url == server.EMPTY_PAGE


async def test_goto_should_navigate_to_about_blank(page, server):
    response = await page.goto("about:blank")
    assert response is None


async def test_goto_should_return_response_when_page_changes_its_URL_after_load(
    page, server
):
    response = await page.goto(server.PREFIX + "/historyapi.html")
    assert response.status == 200


async def test_goto_should_work_with_subframes_return_204(page, server):
    def handle(request):
        request.setResponseCode(204)
        request.finish()

    server.set_route("/frames/frame.html", handle)

    await page.goto(server.PREFIX + "/frames/one-frame.html")


async def test_goto_should_fail_when_server_returns_204(
    page, server, is_chromium, is_webkit
):
    # WebKit just loads an empty page.
    def handle(request):
        request.setResponseCode(204)
        request.finish()

    server.set_route("/empty.html", handle)

    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE)
    assert exc_info.value
    if is_chromium:
        assert "net::ERR_ABORTED" in exc_info.value.message
    elif is_webkit:
        assert "Aborted: 204 No Content" in exc_info.value.message
    else:
        assert "NS_BINDING_ABORTED" in exc_info.value.message


async def test_goto_should_navigate_to_empty_page_with_domcontentloaded(page, server):
    response = await page.goto(server.EMPTY_PAGE, waitUntil="domcontentloaded")
    assert response.status == 200


async def test_goto_should_work_when_page_calls_history_API_in_beforeunload(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
        window.addEventListener('beforeunload', () => history.replaceState(null, 'initial', window.location.href), false)
    }"""
    )

    response = await page.goto(server.PREFIX + "/grid.html")
    assert response.status == 200


async def test_goto_should_fail_when_navigating_to_bad_url(
    page, server, is_chromium, is_webkit
):
    with pytest.raises(Error) as exc_info:
        await page.goto("asdfasdf")
    if is_chromium or is_webkit:
        assert "Cannot navigate to invalid URL" in exc_info.value.message
    else:
        assert "Invalid url" in exc_info.value.message


async def test_goto_should_fail_when_navigating_to_bad_ssl(
    page, https_server, browser_name
):
    with pytest.raises(Error) as exc_info:
        await page.goto(https_server.EMPTY_PAGE)
    expect_ssl_error(exc_info.value.message, browser_name)


async def test_goto_should_fail_when_navigating_to_bad_ssl_after_redirects(
    page, server, https_server, browser_name
):
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/empty.html")
    with pytest.raises(Error) as exc_info:
        await page.goto(https_server.PREFIX + "/redirect/1.html")
    expect_ssl_error(exc_info.value.message, browser_name)


async def test_goto_should_not_crash_when_navigating_to_bad_ssl_after_a_cross_origin_navigation(
    page, server, https_server, browser_name
):
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    with pytest.raises(Error):
        await page.goto(https_server.EMPTY_PAGE)


async def test_goto_should_not_throw_if_networkidle0_is_passed_as_an_option(
    page, server
):
    await page.goto(server.EMPTY_PAGE, waitUntil="networkidle0")


async def test_goto_should_throw_if_networkidle2_is_passed_as_an_option(page, server):
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE, waitUntil="networkidle2")
    assert "Unsupported waitUntil option" in exc_info.value.message


async def test_goto_should_fail_when_main_resources_failed_to_load(
    page, server, is_chromium, is_webkit, is_win
):
    with pytest.raises(Error) as exc_info:
        await page.goto("http://localhost:44123/non-existing-url")
    if is_chromium:
        assert "net::ERR_CONNECTION_REFUSED" in exc_info.value.message
    elif is_webkit and is_win:
        assert "Couldn't connect to server" in exc_info.value.message
    elif is_webkit:
        assert "Could not connect" in exc_info.value.message
    else:
        assert "NS_ERROR_CONNECTION_REFUSED" in exc_info.value.message


async def test_goto_should_fail_when_exceeding_maximum_navigation_timeout(page, server):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html", timeout=1)
    assert "Timeout 1ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_fail_when_exceeding_default_maximum_navigation_timeout(
    page, server
):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.setDefaultNavigationTimeout(2)
    page.setDefaultNavigationTimeout(1)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 1ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_fail_when_exceeding_browser_context_navigation_timeout(
    page, server
):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.setDefaultNavigationTimeout(2)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 2ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_fail_when_exceeding_default_maximum_timeout(page, server):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.setDefaultTimeout(2)
    page.setDefaultTimeout(1)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 1ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_fail_when_exceeding_browser_context_timeout(page, server):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.setDefaultTimeout(2)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 2ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_prioritize_default_navigation_timeout_over_default_timeout(
    page, server
):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.setDefaultTimeout(0)
    page.setDefaultNavigationTimeout(1)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 1ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_disable_timeout_when_its_set_to_0(page, server):
    loaded = []
    page.once("load", lambda: loaded.append(True))
    await page.goto(server.PREFIX + "/grid.html", timeout=0, waitUntil="load")
    assert loaded == [True]


async def test_goto_should_work_when_navigating_to_valid_url(page, server):
    response = await page.goto(server.EMPTY_PAGE)
    assert response.ok


async def test_goto_should_work_when_navigating_to_data_url(page, server):
    response = await page.goto("data:text/html,hello")
    assert response is None


async def test_goto_should_work_when_navigating_to_404(page, server):
    response = await page.goto(server.PREFIX + "/not-found")
    assert response.ok is False
    assert response.status == 404


async def test_goto_should_return_last_response_in_redirect_chain(page, server):
    server.set_redirect("/redirect/1.html", "/redirect/2.html")
    server.set_redirect("/redirect/2.html", "/redirect/3.html")
    server.set_redirect("/redirect/3.html", server.EMPTY_PAGE)
    response = await page.goto(server.PREFIX + "/redirect/1.html")
    assert response.ok
    assert response.url == server.EMPTY_PAGE


async def test_goto_should_navigate_to_data_url_and_not_fire_dataURL_requests(
    page, server
):
    requests = []
    page.on("request", lambda request: requests.append(request))
    dataURL = "data:text/html,<div>yo</div>"
    response = await page.goto(dataURL)
    assert response is None
    assert requests == []


async def test_goto_should_navigate_to_url_with_hash_and_fire_requests_without_hash(
    page, server
):
    requests = []
    page.on("request", lambda request: requests.append(request))
    response = await page.goto(server.EMPTY_PAGE + "#hash")
    assert response.status == 200
    assert response.url == server.EMPTY_PAGE
    assert len(requests) == 1
    assert requests[0].url == server.EMPTY_PAGE


async def test_goto_should_work_with_self_requesting_page(page, server):
    response = await page.goto(server.PREFIX + "/self-request.html")
    assert response.status == 200
    assert "self-request.html" in response.url


async def test_goto_should_fail_when_navigating_and_show_the_url_at_the_error_message(
    page, server, https_server
):
    url = https_server.PREFIX + "/redirect/1.html"
    with pytest.raises(Error) as exc_info:
        await page.goto(url)
    assert url in exc_info.value.message


async def test_goto_should_be_able_to_navigate_to_a_page_controlled_by_service_worker(
    page, server
):
    await page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")
    await page.evaluate("window.activationPromise")
    await page.goto(server.PREFIX + "/serviceworkers/fetch/sw.html")


async def test_goto_should_send_referer(page, server):
    [request1, request2, _] = await asyncio.gather(
        server.wait_for_request("/grid.html"),
        server.wait_for_request("/digits/1.png"),
        page.goto(server.PREFIX + "/grid.html", referer="http://google.com/"),
    )
    assert request1.getHeader("referer") == "http://google.com/"
    # Make sure subresources do not inherit referer.
    assert request2.getHeader("referer") == server.PREFIX + "/grid.html"
    assert page.url == server.PREFIX + "/grid.html"


async def test_goto_should_reject_referer_option_when_set_extra_http_headers_provides_referer(
    page, server
):
    await page.setExtraHTTPHeaders({"referer": "http://microsoft.com/"})
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/grid.html", referer="http://google.com/")
    assert (
        '"referer" is already specified as extra HTTP header' in exc_info.value.message
    )
    assert server.PREFIX + "/grid.html" in exc_info.value.message


async def test_network_idle_should_navigate_to_empty_page_with_networkidle(
    page, server
):
    response = await page.goto(server.EMPTY_PAGE, waitUntil="networkidle")
    assert response.status == 200


async def test_wait_for_nav_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    [response, _] = await asyncio.gather(
        page.waitForNavigation(),
        page.evaluate(
            "url => window.location.href = url", server.PREFIX + "/grid.html"
        ),
    )
    assert response.ok
    assert "grid.html" in response.url


async def test_wait_for_nav_should_respect_timeout(page, server):
    asyncio.create_task(page.goto(server.EMPTY_PAGE))
    with pytest.raises(Error) as exc_info:
        await page.waitForNavigation(url="**/frame.html", timeout=5000)
    assert "Timeout 5000ms exceeded" in exc_info.value.message
    # TODO: implement logging
    # assert 'waiting for navigation to "**/frame.html" until "load"' in exc_info.value.message
    # assert f'navigated to "{server.EMPTY_PAGE}"' in exc_info.value.message


def expect_ssl_error(error_message: str, browser_name: str) -> None:
    if browser_name == "chromium":
        assert "net::ERR_CERT_AUTHORITY_INVALID" in error_message
    elif browser_name == "webkit":
        if sys.platform == "darwin":
            assert "The certificate for this server is invalid" in error_message
        elif sys.platform == "win32":
            assert "SSL connect error" in error_message
        else:
            assert "Unacceptable TLS certificate" in error_message
    else:
        assert "SSL_ERROR_UNKNOWN" in error_message
