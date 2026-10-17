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

"""Port of tests/page/frame-evaluate.spec.ts."""

import asyncio

import pytest

from playwright.async_api import Error, Page
from tests.server import Server

from ..utils import Utils


async def test_FR_001_should_have_different_execution_contexts(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(page.frames) == 2
    await page.frames[0].evaluate("() => window['FOO'] = 'foo'")
    await page.frames[1].evaluate("() => window['FOO'] = 'bar'")
    assert await page.frames[0].evaluate("() => window['FOO']") == "foo"
    assert await page.frames[1].evaluate("() => window['FOO']") == "bar"


async def test_FR_002_should_have_correct_execution_contexts_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert len(page.frames) == 2
    assert await page.frames[0].evaluate("() => document.body.textContent.trim()") == ""
    assert (
        await page.frames[1].evaluate("() => document.body.textContent.trim()")
        == "Hi, I'm frame"
    )


async def test_FR_005_should_execute_after_cross_site_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    main_frame = page.main_frame
    assert server.EMPTY_PAGE in await main_frame.evaluate("() => window.location.href")
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert server.CROSS_PROCESS_PREFIX in await main_frame.evaluate(
        "() => window.location.href"
    )


async def test_FR_006_should_not_allow_cross_frame_js_handles(
    page: Page, server: Server
) -> None:
    # TODO: this should actually be possible because frames script each other,
    # but protocol implementations do not support this. For now, assume current
    # behavior.
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    handle = await page.evaluate_handle(
        """() => {
        const iframe = document.querySelector('iframe');
        const foo = { bar: 'baz' };
        iframe.contentWindow['__foo'] = foo;
        return foo;
    }"""
    )
    child_frame = page.main_frame.child_frames[0]
    child_result = await child_frame.evaluate("() => window['__foo']")
    assert child_result == {"bar": "baz"}
    with pytest.raises(Error) as exc_info:
        await child_frame.evaluate("foo => foo.bar", handle)
    assert (
        "JSHandles can be evaluated only in the context they were created!"
        in exc_info.value.message
    )


async def test_FR_007_should_allow_cross_frame_element_handles(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    body_handle = await page.main_frame.child_frames[0].query_selector("body")
    result = await page.evaluate("body => body.innerHTML", body_handle)
    assert result.strip() == "<div>Hi, I'm frame</div>"


async def test_FR_008_should_not_allow_cross_frame_element_handles_when_frames_do_not_script_each_other(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    frame = await utils.attach_frame(
        page, "frame1", server.CROSS_PROCESS_PREFIX + "/empty.html"
    )
    body_handle = await frame.query_selector("body")
    with pytest.raises(Error) as exc_info:
        await page.evaluate("body => body.innerHTML", body_handle)
    assert (
        "Unable to adopt element handle from a different document"
        in exc_info.value.message
    )


async def test_FR_009_should_throw_for_detached_frames(
    page: Page, server: Server, utils: Utils
) -> None:
    frame1 = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.detach_frame(page, "frame1")
    with pytest.raises(Error) as exc_info:
        await frame1.evaluate("() => 7 * 8")
    assert "Frame.evaluate: Frame was detached" in exc_info.value.message


async def test_FR_010_should_be_isolated_between_frames(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(page.frames) == 2
    [frame1, frame2] = page.frames
    assert frame1 != frame2

    await asyncio.gather(
        frame1.evaluate("() => window['a'] = 1"),
        frame2.evaluate("() => window['a'] = 2"),
    )
    [a1, a2] = await asyncio.gather(
        frame1.evaluate("() => window['a']"),
        frame2.evaluate("() => window['a']"),
    )
    assert a1 == 1
    assert a2 == 2


async def test_FR_011_should_work_in_iframes_that_failed_initial_navigation(
    page: Page, browser_name: str
) -> None:
    await page.set_content(
        """
    <meta http-equiv="Content-Security-Policy" content="script-src 'none';">
    <iframe src='javascript:""'></iframe>
  """,
        wait_until="domcontentloaded",
    )
    await page.evaluate(
        """() => {
        const iframe = document.querySelector('iframe');
        const div = iframe.contentDocument.createElement('div');
        iframe.contentDocument.body.appendChild(div);
    }"""
    )
    assert page.frames[1].url == ("about:blank" if browser_name == "webkit" else "")
    # Main world should work.
    assert await page.frames[1].evaluate("() => window.location.href") == "about:blank"
    # Utility world should work.
    assert await page.frames[1].query_selector("div")


async def test_FR_012_should_work_in_iframes_that_interrupted_initial_javascript_url_navigation(
    page: Page, server: Server
) -> None:
    # Chromium does not report isolated world for the iframe.
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
        const iframe = document.createElement('iframe');
        iframe.src = 'javascript:""';
        document.body.appendChild(iframe);
        iframe.contentDocument.open();
        iframe.contentDocument.write('<div>hello</div>');
        iframe.contentDocument.close();
    }"""
    )
    # Main world should work.
    assert (
        await page.frames[1].evaluate("() => window.top.location.href")
        == server.EMPTY_PAGE
    )
    # Utility world should work.
    assert await page.frames[1].query_selector("div")


async def test_FR_013_evaluate_handle_should_work(page: Page, server: Server) -> None:
    await page.goto(server.EMPTY_PAGE)
    main_frame = page.main_frame
    window_handle = await main_frame.evaluate_handle("() => window")
    assert window_handle
