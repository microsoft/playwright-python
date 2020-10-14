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

import pytest

from playwright import Error
from playwright.async_api import BrowserType


async def test_browser_type_launch_should_reject_all_promises_when_browser_is_closed(
    browser_type: BrowserType, launch_arguments
):
    browser = await browser_type.launch(**launch_arguments)
    page = await (await browser.newContext()).newPage()
    never_resolves = asyncio.create_task(page.evaluate("() => new Promise(r => {})"))
    await page.close()
    with pytest.raises(Error) as exc:
        await never_resolves
    assert "Protocol error" in exc.value.message


@pytest.mark.skip_browser("firefox")
async def test_browser_type_launch_should_throw_if_page_argument_is_passed(
    browser_type, launch_arguments
):
    with pytest.raises(Error) as exc:
        await browser_type.launch(**launch_arguments, args=["http://example.com"])
    assert "can not specify page" in exc.value.message


@pytest.mark.skip("currently disabled on upstream")
async def test_browser_type_launch_should_reject_if_launched_browser_fails_immediately(
    browser_type, launch_arguments, assetdir
):
    with pytest.raises(Error):
        await browser_type.launch(
            **launch_arguments,
            executablePath=assetdir / "dummy_bad_browser_executable.js"
        )


@pytest.mark.skip(
    "does not return the expected error"
)  # TODO: hangs currently on the bots
async def test_browser_type_launch_should_reject_if_executable_path_is_invalid(
    browser_type, launch_arguments
):
    with pytest.raises(Error) as exc:
        await browser_type.launch(
            **launch_arguments, executablePath="random-invalid-path"
        )
    assert "Failed to launch" in exc.value.message


@pytest.mark.skip()
async def test_browser_type_launch_server_should_return_child_process_instance(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    assert browser_server.pid > 0
    await browser_server.close()


@pytest.mark.skip()
async def test_browser_type_launch_server_should_fire_close_event(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    close_event = asyncio.Future()
    browser_server.on("close", lambda: close_event.set_result(None))
    await asyncio.gather(close_event, browser_server.close())


async def test_browser_type_executable_path_should_work(browser_type):
    executable_path = browser_type.executablePath
    assert os.path.exists(executable_path)
    assert os.path.realpath(executable_path) == os.path.realpath(executable_path)


async def test_browser_type_name_should_work(
    browser_type, is_webkit, is_firefox, is_chromium
):
    if is_webkit:
        assert browser_type.name == "webkit"
    elif is_firefox:
        assert browser_type.name == "firefox"
    elif is_chromium:
        assert browser_type.name == "chromium"
    else:
        raise ValueError("Unknown browser")


@pytest.mark.skip()
async def test_browser_is_connected_should_set_connected_state(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    assert remote.isConnected()
    await remote.close()
    assert remote.isConnected() is False
    await browser_server.close()


@pytest.mark.skip()
async def test_browser_is_connected_should_throw_when_used_after_isConnected_returns_false(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    page = await remote.newPage()
    disconnected_future = asyncio.Future()
    remote.once("disconnected", lambda: disconnected_future.set_result(None))
    await asyncio.gather(browser_server.close(), disconnected_future)
    assert remote.isConnected() is False
    with pytest.raises(Error) as exc:
        await page.evaluate('"1 + 1"')
    assert "has been closed" in exc.value.message


@pytest.mark.skip()
async def test_browser_disconnect_should_reject_navigation_when_browser_closes(
    browser_type, launch_arguments, server
):
    server.set_route("/one-style.css", lambda r: None)
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    page = await remote.newPage()

    async def handle_goto():
        with pytest.raises(Error) as exc:
            await page.goto(server.PREFIX + "/one-style.html", timeout=60000)
        assert "Navigation failed because page was closed!" in exc.value.message

    wait_for_request = asyncio.create_task(server.wait_for_request("/one-style.css"))
    goto_assert = asyncio.create_task(handle_goto())
    await wait_for_request
    await remote.close()
    await goto_assert
    await browser_server.close()


@pytest.mark.skip()
async def test_browser_disconnect_should_reject_waitForSelector_when_browser_closes(
    browser_type, launch_arguments, server
):
    server.set_route("/empty.html", lambda r: None)
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    page = await remote.newPage()
    wait_for_selector_future = asyncio.Future()

    async def handle_wait_for_selector():
        try:
            await page.waitForSelector("div", state="attached", timeout=60000)
        except Error as exc:
            wait_for_selector_future.set_result(exc)

    # Make sure the previous waitForSelector has time to make it to the browser before we disconnect.
    asyncio.create_task(handle_wait_for_selector())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    await page.waitForSelector("body", state="attached")

    await remote.close()
    error = await wait_for_selector_future
    assert "Protocol error" in error.message
    await browser_server.close()


@pytest.mark.skip()
async def test_browser_disconnect_should_throw_if_used_after_disconnect(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    page = await remote.newPage()
    await remote.close()
    with pytest.raises(Error) as exc:
        await page.evaluate('"1 + 1"')
    assert "has been closed" in exc.value.message
    await browser_server.close()


@pytest.mark.skip()
async def test_browser_disconnect_should_emit_close_events_on_pages_and_contexts(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    context = await remote.newContext()
    page = await context.newPage()
    pages_closed = []
    page.on("close", lambda: pages_closed.append(True))
    context_close_fixture = asyncio.Future()
    context.on("close", lambda: context_close_fixture.set_result(None))
    await asyncio.gather(context_close_fixture, browser_server.close())
    assert len(pages_closed) == 1


@pytest.mark.skip()
async def test_browser_close_should_terminate_network_waiters(
    browser_type, launch_arguments, server
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    remote = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    new_page = await remote.newPage()
    wait_for_request_future = asyncio.Future()

    async def handle_waitForRequest():
        try:
            await new_page.waitForRequest(server.EMPTY_PAGE)
        except Error as exc:
            wait_for_request_future.set_result(exc)

    wait_for_response_future = asyncio.Future()

    async def handle_waitForResponse():
        try:
            await new_page.waitForResponse(server.EMPTY_PAGE)
        except Error as exc:
            wait_for_response_future.set_result(exc)

    asyncio.create_task(handle_waitForRequest())
    asyncio.create_task(handle_waitForResponse())
    await asyncio.sleep(0)  # execute scheduled tasks, but don't await them
    results = await asyncio.gather(
        wait_for_request_future,
        wait_for_response_future,
        browser_server.close(),
    )
    for i in range(2):
        message = results[i].message
        assert "Page closed" in message
        assert "Timeout" not in message


async def test_browser_close_should_fire_close_event_for_all_contexts(
    browser_type, launch_arguments
):
    browser = await browser_type.launch(**launch_arguments)
    context = await browser.newContext()
    closed = []
    context.on("close", lambda: closed.append(True))
    await browser.close()
    assert closed == [True]


async def test_browser_close_should_be_callable_twice(browser_type, launch_arguments):
    browser = await browser_type.launch(**launch_arguments)
    await asyncio.gather(
        browser.close(),
        browser.close(),
    )
    await browser.close()


@pytest.mark.skip()
async def test_browser_type_launch_server_should_work(browser_type, launch_arguments):
    browser_server = await browser_type.launchServer(**launch_arguments)
    browser = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    browser_context = await browser.newContext()
    assert len(browser_context.pages) == 0
    assert browser_server.wsEndpoint
    page = await browser_context.newPage()
    assert await page.evaluate("11 * 11") == 121
    await page.close()
    await browser.close()
    await browser_server.close()


@pytest.mark.skip()
async def test_browser_type_launch_server_should_fire_disconnected_when_closing_the_server(
    browser_type, launch_arguments
):
    browser_server = await browser_type.launchServer(**launch_arguments)
    browser = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)

    disconnected_promise = asyncio.Future()
    browser.once("disconnected", lambda: disconnected_promise.set_result(None))

    closed_promise = asyncio.Future()
    browser_server.on("close", lambda: closed_promise.set_result(None))

    await browser_server.kill()
    await asyncio.gather(
        disconnected_promise,
        closed_promise,
    )


@pytest.mark.skip()
async def test_browser_type_launch_server_should_fire_close_event_during_kill(
    browser_type, launch_arguments
):
    order = []
    browser_server = await browser_type.launchServer(**launch_arguments)

    closed_promise = asyncio.Future()
    browser_server.on(
        "close", lambda: (order.append("closed"), closed_promise.set_result(None))
    )

    async def kill_with_order():
        await browser_server.kill()
        order.append("killed")

    await asyncio.gather(kill_with_order(), closed_promise)
    assert order == ["closed", "killed"]


@pytest.mark.skip()
async def test_browser_type_connect_should_be_able_to_reconnect_to_a_browser(
    browser_type, launch_arguments, server
):
    browser_server = await browser_type.launchServer(**launch_arguments)

    browser = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    browser_context = await browser.newContext()
    page = await browser_context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await browser.close()

    browser = await browser_type.connect(wsEndpoint=browser_server.wsEndpoint)
    browser_context = await browser.newContext()
    page = await browser_context.newPage()
    await page.goto(server.EMPTY_PAGE)
    await browser.close()

    await browser_server.close()
