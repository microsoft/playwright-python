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
import re
import sys
from typing import Any

import pytest

from playwright.async_api import Error, Request, TimeoutError


async def test_goto_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    assert page.url == server.EMPTY_PAGE


async def test_goto_should_work_with_file_URL(page, server, assetdir):
    fileurl = (assetdir / "frames" / "two-frames.html").as_uri()
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
    assert response.frame == page.main_frame
    assert request_frames[0] == page.main_frame
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
    assert response.frame == page.main_frame
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
    assert response.frame == page.main_frame
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


async def test_goto_should_return_response_when_page_changes_its_url_after_load(
    page, server
):
    response = await page.goto(server.PREFIX + "/historyapi.html")
    assert response.status == 200


@pytest.mark.skip_browser("firefox")
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
    response = await page.goto(server.EMPTY_PAGE, wait_until="domcontentloaded")
    assert response.status == 200


async def test_goto_should_work_when_page_calls_history_api_in_beforeunload(
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


async def test_goto_should_throw_if_networkidle2_is_passed_as_an_option(page, server):
    with pytest.raises(Error) as exc_info:
        await page.goto(server.EMPTY_PAGE, wait_until="networkidle2")
    assert (
        "wait_until: expected one of (load|domcontentloaded|networkidle)"
        in exc_info.value.message
    )


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
    page.context.set_default_navigation_timeout(2)
    page.set_default_navigation_timeout(1)
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
    page.context.set_default_navigation_timeout(2)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 2ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_fail_when_exceeding_default_maximum_timeout(page, server):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.set_default_timeout(2)
    page.set_default_timeout(1)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 1ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_fail_when_exceeding_browser_context_timeout(page, server):
    # Hang for request to the empty.html
    server.set_route("/empty.html", lambda request: None)
    page.context.set_default_timeout(2)
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
    page.set_default_timeout(0)
    page.set_default_navigation_timeout(1)
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/empty.html")
    assert "Timeout 1ms exceeded" in exc_info.value.message
    assert server.PREFIX + "/empty.html" in exc_info.value.message
    assert isinstance(exc_info.value, TimeoutError)


async def test_goto_should_disable_timeout_when_its_set_to_0(page, server):
    loaded = []
    page.once("load", lambda: loaded.append(True))
    await page.goto(server.PREFIX + "/grid.html", timeout=0, wait_until="load")
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
    await page.set_extra_http_headers({"referer": "http://microsoft.com/"})
    with pytest.raises(Error) as exc_info:
        await page.goto(server.PREFIX + "/grid.html", referer="http://google.com/")
    assert (
        '"referer" is already specified as extra HTTP header' in exc_info.value.message
    )
    assert server.PREFIX + "/grid.html" in exc_info.value.message


async def test_network_idle_should_navigate_to_empty_page_with_networkidle(
    page, server
):
    response = await page.goto(server.EMPTY_PAGE, wait_until="networkidle")
    assert response.status == 200


async def test_wait_for_nav_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_navigation() as response_info:
        await page.evaluate(
            "url => window.location.href = url", server.PREFIX + "/grid.html"
        )
    response = await response_info.value
    assert response.ok
    assert "grid.html" in response.url


async def test_wait_for_nav_should_respect_timeout(page, server):
    with pytest.raises(Error) as exc_info:
        async with page.expect_navigation(url="**/frame.html", timeout=2500):
            await page.goto(server.EMPTY_PAGE)
    assert "Timeout 2500ms exceeded" in exc_info.value.message


async def test_wait_for_nav_should_work_with_both_domcontentloaded_and_load(
    page, server
):
    async with page.expect_navigation(
        wait_until="domcontentloaded"
    ), page.expect_navigation(wait_until="load"):
        await page.goto(server.PREFIX + "/one-style.html")


async def test_wait_for_nav_should_work_with_clicking_on_anchor_links(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content('<a href="#foobar">foobar</a>')
    async with page.expect_navigation() as response_info:
        await page.click("a"),
    response = await response_info.value
    assert response is None
    assert page.url == server.EMPTY_PAGE + "#foobar"


async def test_wait_for_nav_should_work_with_clicking_on_links_which_do_not_commit_navigation(
    page, server, https_server, browser_name
):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(f"<a href='{https_server.EMPTY_PAGE}'>foobar</a>")
    with pytest.raises(Error) as exc_info:
        async with page.expect_navigation():
            await page.click("a"),
    expect_ssl_error(exc_info.value.message, browser_name)


async def test_wait_for_nav_should_work_with_history_push_state(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <a onclick='javascript:pushState()'>SPA</a>
        <script>
            function pushState() { history.pushState({}, '', 'wow.html') }
        </script>
    """
    )
    async with page.expect_navigation() as response_info:
        await page.click("a"),
    response = await response_info.value
    assert response is None
    assert page.url == server.PREFIX + "/wow.html"


async def test_wait_for_nav_should_work_with_history_replace_state(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
        <a onclick='javascript:replaceState()'>SPA</a>
        <script>
            function replaceState() { history.replaceState({}, '', '/replaced.html') }
        </script>
    """
    )
    async with page.expect_navigation() as response_info:
        await page.click("a"),
    response = await response_info.value
    assert response is None
    assert page.url == server.PREFIX + "/replaced.html"


async def test_wait_for_nav_should_work_with_dom_history_back_forward(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
      <a id=back onclick='javascript:go_back()'>back</a>
      <a id=forward onclick='javascript:go_forward()'>forward</a>
      <script>
        function go_back() { history.back(); }
        function go_forward() { history.forward(); }
        history.pushState({}, '', '/first.html')
        history.pushState({}, '', '/second.html')
      </script>
    """
    )
    assert page.url == server.PREFIX + "/second.html"
    async with page.expect_navigation() as back_response_info:
        await page.click("a#back"),
    back_response = await back_response_info.value
    assert back_response is None
    assert page.url == server.PREFIX + "/first.html"
    async with page.expect_navigation() as forward_response_info:
        await page.click("a#forward"),
    forward_response = await forward_response_info.value
    assert forward_response is None
    assert page.url == server.PREFIX + "/second.html"


async def test_wait_for_nav_should_work_when_subframe_issues_window_stop(page, server):
    server.set_route("/frames/style.css", lambda _: None)
    navigation_promise = asyncio.create_task(
        page.goto(server.PREFIX + "/frames/one-frame.html")
    )
    await asyncio.sleep(0)
    async with page.expect_event("frameattached") as frame_info:
        pass
    frame = await frame_info.value

    async with page.expect_event("framenavigated", lambda f: f == frame):
        pass
    await asyncio.gather(frame.evaluate("() => window.stop()"), navigation_promise)


async def test_wait_for_nav_should_work_with_url_match(page, server):
    responses = [None, None, None]

    async def wait_for_nav(url: Any, index: int) -> None:
        async with page.expect_navigation(url=url) as response_info:
            pass
        responses[index] = await response_info.value

    response0_promise = asyncio.create_task(
        wait_for_nav(re.compile(r"one-style\.html"), 0)
    )
    response1_promise = asyncio.create_task(
        wait_for_nav(re.compile(r"\/frame.html"), 1)
    )
    response2_promise = asyncio.create_task(
        wait_for_nav(lambda url: "foo=bar" in url, 2)
    )
    assert responses == [None, None, None]
    await page.goto(server.EMPTY_PAGE)
    assert responses == [None, None, None]
    await page.goto(server.PREFIX + "/frame.html")
    assert responses[0] is None
    await response1_promise
    assert responses[1] is not None
    assert responses[2] is None
    await page.goto(server.PREFIX + "/one-style.html")
    await response0_promise
    assert responses[0] is not None
    assert responses[1] is not None
    assert responses[2] is None
    await page.goto(server.PREFIX + "/frame.html?foo=bar")
    await response2_promise
    assert responses[0] is not None
    assert responses[1] is not None
    assert responses[2] is not None
    await page.goto(server.PREFIX + "/empty.html")
    assert responses[0].url == server.PREFIX + "/one-style.html"
    assert responses[1].url == server.PREFIX + "/frame.html"
    assert responses[2].url == server.PREFIX + "/frame.html?foo=bar"


async def test_wait_for_nav_should_work_with_url_match_for_same_document_navigations(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_navigation(url=re.compile(r"third\.html")) as response_info:
        assert not response_info.is_done()
        await page.evaluate("history.pushState({}, '', '/first.html')")
        assert not response_info.is_done()
        await page.evaluate("history.pushState({}, '', '/second.html')")
        assert not response_info.is_done()
        await page.evaluate("history.pushState({}, '', '/third.html')")
    assert response_info.is_done()


async def test_wait_for_nav_should_work_for_cross_process_navigations(page, server):
    await page.goto(server.EMPTY_PAGE)
    url = server.CROSS_PROCESS_PREFIX + "/empty.html"
    async with page.expect_navigation(wait_until="domcontentloaded") as response_info:
        await page.goto(url)
    response = await response_info.value
    assert response.url == url
    assert page.url == url
    assert await page.evaluate("document.location.href") == url


async def test_expect_navigation_should_work_for_cross_process_navigations(
    page, server
):
    await page.goto(server.EMPTY_PAGE)
    url = server.CROSS_PROCESS_PREFIX + "/empty.html"
    async with page.expect_navigation(wait_until="domcontentloaded") as response_info:
        goto_task = asyncio.create_task(page.goto(url))
    response = await response_info.value
    assert response.url == url
    assert page.url == url
    assert await page.evaluate("document.location.href") == url
    await goto_task


async def test_wait_for_load_state_should_respect_timeout(page, server):
    requests = []

    def handler(request: Any):
        requests.append(request)

    server.set_route("/one-style.css", handler)

    await page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_load_state("load", timeout=1)
    assert "Timeout 1ms exceeded." in exc_info.value.message


async def test_wait_for_load_state_should_resolve_immediately_if_loaded(page, server):
    await page.goto(server.PREFIX + "/one-style.html")
    await page.wait_for_load_state()


async def test_wait_for_load_state_should_throw_for_bad_state(page, server):
    await page.goto(server.PREFIX + "/one-style.html")
    with pytest.raises(Error) as exc_info:
        await page.wait_for_load_state("bad")
    assert (
        "state: expected one of (load|domcontentloaded|networkidle)"
        in exc_info.value.message
    )


async def test_wait_for_load_state_should_resolve_immediately_if_load_state_matches(
    page, server
):
    await page.goto(server.EMPTY_PAGE)

    requests = []

    def handler(request: Any):
        requests.append(request)

    server.set_route("/one-style.css", handler)

    await page.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    await page.wait_for_load_state("domcontentloaded")


async def test_wait_for_load_state_should_work_with_pages_that_have_loaded_before_being_connected_to(
    page, context, server
):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("window._popup = window.open(document.location.href)")

    # The url is about:blank in FF.
    popup = await popup_info.value
    assert popup.url == server.EMPTY_PAGE
    await popup.wait_for_load_state()
    assert popup.url == server.EMPTY_PAGE


async def test_wait_for_load_state_should_wait_for_load_state_of_empty_url_popup(
    browser, page, is_firefox
):
    ready_state = []
    async with page.expect_popup() as popup_info:
        ready_state.append(
            await page.evaluate(
                """() => {
            popup = window.open('')
            return popup.document.readyState
        }"""
            )
        )

    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert ready_state == ["uninitialized"] if is_firefox else ["complete"]
    assert await popup.evaluate("() => document.readyState") == ready_state[0]


async def test_wait_for_load_state_should_wait_for_load_state_of_about_blank_popup_(
    browser, page
):
    async with page.expect_popup() as popup_info:
        await page.evaluate("window.open('about:blank') && 1")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("document.readyState") == "complete"


async def test_wait_for_load_state_should_wait_for_load_state_of_about_blank_popup_with_noopener(
    browser, page
):
    async with page.expect_popup() as popup_info:
        await page.evaluate("window.open('about:blank', null, 'noopener') && 1")

    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("document.readyState") == "complete"


async def test_wait_for_load_state_should_wait_for_load_state_of_popup_with_network_url_(
    browser, page, server
):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate("url => window.open(url) && 1", server.EMPTY_PAGE)

    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("document.readyState") == "complete"


async def test_wait_for_load_state_should_wait_for_load_state_of_popup_with_network_url_and_noopener_(
    browser, page, server
):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.open(url, null, 'noopener') && 1", server.EMPTY_PAGE
        )

    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("document.readyState") == "complete"


async def test_wait_for_load_state_should_work_with_clicking_target__blank(
    browser, page, server
):
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        '<a target=_blank rel="opener" href="/one-style.html">yo</a>'
    )
    async with page.expect_popup() as popup_info:
        await page.click("a")
    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert await popup.evaluate("document.readyState") == "complete"


async def test_wait_for_load_state_should_wait_for_load_state_of_new_page(
    context, page, server
):
    async with context.expect_page() as page_info:
        await context.new_page()
    new_page = await page_info.value
    await new_page.wait_for_load_state()
    assert await new_page.evaluate("document.readyState") == "complete"


async def test_wait_for_load_state_in_popup(context, server):
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    css_requests = []

    def handle_request(request):
        css_requests.append(request)
        request.write(b"body {}")
        request.finish()

    server.set_route("/one-style.css", handle_request)

    async with page.expect_popup() as popup_info:
        await page.evaluate(
            "url => window.popup = window.open(url)", server.PREFIX + "/one-style.html"
        )

    popup = await popup_info.value
    await popup.wait_for_load_state()
    assert len(css_requests)


async def test_go_back_should_work(page, server):
    assert await page.go_back() is None

    await page.goto(server.EMPTY_PAGE)
    await page.goto(server.PREFIX + "/grid.html")

    response = await page.go_back()
    assert response.ok
    assert server.EMPTY_PAGE in response.url

    response = await page.go_forward()
    assert response.ok
    assert "/grid.html" in response.url

    response = await page.go_forward()
    assert response is None


async def test_go_back_should_work_with_history_api(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
        history.pushState({}, '', '/first.html')
        history.pushState({}, '', '/second.html')
    }"""
    )
    assert page.url == server.PREFIX + "/second.html"

    await page.go_back()
    assert page.url == server.PREFIX + "/first.html"
    await page.go_back()
    assert page.url == server.EMPTY_PAGE
    await page.go_forward()
    assert page.url == server.PREFIX + "/first.html"


async def test_frame_goto_should_navigate_subframes(page, server):
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert "/frames/one-frame.html" in page.frames[0].url
    assert "/frames/frame.html" in page.frames[1].url

    response = await page.frames[1].goto(server.EMPTY_PAGE)
    assert response.ok
    assert response.frame == page.frames[1]


async def test_frame_goto_should_reject_when_frame_detaches(page, server):
    await page.goto(server.PREFIX + "/frames/one-frame.html")

    await page.route("**/empty.html", lambda route, request: None)
    navigation_task = asyncio.create_task(page.frames[1].goto(server.EMPTY_PAGE))
    asyncio.create_task(page.eval_on_selector("iframe", "frame => frame.remove()"))
    with pytest.raises(Error) as exc_info:
        await navigation_task
    assert "frame was detached" in exc_info.value.message


async def test_frame_goto_should_continue_after_client_redirect(page, server):
    server.set_route("/frames/script.js", lambda _: None)
    url = server.PREFIX + "/frames/child-redirect.html"

    with pytest.raises(Error) as exc_info:
        await page.goto(url, timeout=2500, wait_until="networkidle")

    assert "Timeout 2500ms exceeded." in exc_info.value.message
    assert (
        f'navigating to "{url}", waiting until "networkidle"' in exc_info.value.message
    )


async def test_frame_wait_for_nav_should_work(page, server):
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]
    async with frame.expect_navigation() as response_info:
        await frame.evaluate(
            "url => window.location.href = url", server.PREFIX + "/grid.html"
        )
    response = await response_info.value
    assert response.ok
    assert "grid.html" in response.url
    assert response.frame == frame
    assert "/frames/one-frame.html" in page.url


async def test_frame_wait_for_nav_should_fail_when_frame_detaches(page, server):
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]
    server.set_route("/empty.html", lambda _: None)
    with pytest.raises(Error) as exc_info:
        async with frame.expect_navigation():
            await asyncio.gather(
                frame.evaluate('window.location = "/empty.html"'),
                page.evaluate(
                    'setTimeout(() => document.querySelector("iframe").remove())'
                ),
            )
    assert "frame was detached" in exc_info.value.message


async def test_frame_wait_for_load_state_should_work(page, server):
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    frame = page.frames[1]

    request_future = asyncio.Future()
    await page.route(
        server.PREFIX + "/one-style.css",
        lambda route, request: request_future.set_result(route),
    )

    await frame.goto(server.PREFIX + "/one-style.html", wait_until="domcontentloaded")
    request = await request_future
    load_task = asyncio.create_task(frame.wait_for_load_state())
    # give the promise a chance to resolve, even though it shouldn't
    await page.evaluate("1")
    assert not load_task.done()
    asyncio.create_task(request.continue_())
    await load_task


async def test_reload_should_work(page, server):
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("window._foo = 10")
    await page.reload()
    assert await page.evaluate("window._foo") is None


async def test_reload_should_work_with_data_url(page, server):
    await page.goto("data:text/html,hello")
    assert "hello" in await page.content()
    assert await page.reload() is None
    assert "hello" in await page.content()


async def test_should_work_with__blank_target(page, server):
    def handler(request):
        request.write(
            f'<a href="{server.EMPTY_PAGE}" target="_blank">Click me</a>'.encode()
        )
        request.finish()

    server.set_route("/empty.html", handler)

    await page.goto(server.EMPTY_PAGE)
    await page.click('"Click me"')


async def test_should_work_with_cross_process__blank_target(page, server):
    def handler(request):
        request.write(
            f'<a href="{server.CROSS_PROCESS_PREFIX}/empty.html" target="_blank">Click me</a>'.encode()
        )
        request.finish()

    server.set_route("/empty.html", handler)

    await page.goto(server.EMPTY_PAGE)
    await page.click('"Click me"')


def expect_ssl_error(error_message: str, browser_name: str) -> None:
    if browser_name == "chromium":
        assert "net::ERR_CERT_AUTHORITY_INVALID" in error_message
    elif browser_name == "webkit":
        if sys.platform == "darwin":
            assert "The certificate for this server is invalid" in error_message
        elif sys.platform == "win32":
            assert "SSL peer certificate or SSH remote key was not OK" in error_message
        else:
            assert "Unacceptable TLS certificate" in error_message
    else:
        assert "SSL_ERROR_UNKNOWN" in error_message
