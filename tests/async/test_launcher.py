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

from playwright.async_api import BrowserType, Error


async def test_browser_type_launch_should_reject_all_promises_when_browser_is_closed(
    browser_type: BrowserType, launch_arguments
):
    browser = await browser_type.launch(**launch_arguments)
    page = await (await browser.new_context()).new_page()
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
            executable_path=assetdir / "dummy_bad_browser_executable.js"
        )


@pytest.mark.skip(
    "does not return the expected error"
)  # TODO: hangs currently on the bots
async def test_browser_type_launch_should_reject_if_executable_path_is_invalid(
    browser_type, launch_arguments
):
    with pytest.raises(Error) as exc:
        await browser_type.launch(
            **launch_arguments, executable_path="random-invalid-path"
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
    executable_path = browser_type.executable_path
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


async def test_browser_close_should_fire_close_event_for_all_contexts(
    browser_type, launch_arguments
):
    browser = await browser_type.launch(**launch_arguments)
    context = await browser.new_context()
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
