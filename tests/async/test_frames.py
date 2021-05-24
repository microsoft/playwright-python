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

from playwright.async_api import Error


async def test_evaluate_handle(page, server):
    await page.goto(server.EMPTY_PAGE)
    main_frame = page.main_frame
    assert main_frame.page == page
    window_handle = await main_frame.evaluate_handle("window")
    assert window_handle


async def test_frame_element(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    frame1 = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    frame3 = await utils.attach_frame(page, "frame3", server.EMPTY_PAGE)
    frame1handle1 = await page.query_selector("#frame1")
    frame1handle2 = await frame1.frame_element()
    frame3handle1 = await page.query_selector("#frame3")
    frame3handle2 = await frame3.frame_element()
    assert await frame1handle1.evaluate("(a, b) => a === b", frame1handle2)
    assert await frame3handle1.evaluate("(a, b) => a === b", frame3handle2)
    assert await frame1handle1.evaluate("(a, b) => a === b", frame3handle1) is False


async def test_frame_element_with_content_frame(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    frame = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    handle = await frame.frame_element()
    content_frame = await handle.content_frame()
    assert content_frame == frame


async def test_frame_element_throw_when_detached(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    frame1 = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await page.eval_on_selector("#frame1", "e => e.remove()")
    error = None
    try:
        await frame1.frame_element()
    except Error as e:
        error = e
    assert error.message == "Frame has been detached."


async def test_evaluate_throw_for_detached_frames(page, server, utils):
    frame1 = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.detach_frame(page, "frame1")
    error = None
    try:
        await frame1.evaluate("7 * 8")
    except Error as e:
        error = e
    assert "Execution Context is not available in detached frame" in error.message


async def test_evaluate_isolated_between_frames(page, server, utils):
    await page.goto(server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    assert len(page.frames) == 2
    [frame1, frame2] = page.frames
    assert frame1 != frame2

    await asyncio.gather(
        frame1.evaluate("window.a = 1"), frame2.evaluate("window.a = 2")
    )
    [a1, a2] = await asyncio.gather(
        frame1.evaluate("window.a"), frame2.evaluate("window.a")
    )
    assert a1 == 1
    assert a2 == 2


async def test_should_handle_nested_frames(page, server, utils):
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    assert utils.dump_frames(page.main_frame) == [
        "http://localhost:<PORT>/frames/nested-frames.html",
        "    http://localhost:<PORT>/frames/frame.html (aframe)",
        "    http://localhost:<PORT>/frames/two-frames.html (2frames)",
        "        http://localhost:<PORT>/frames/frame.html (dos)",
        "        http://localhost:<PORT>/frames/frame.html (uno)",
    ]


async def test_should_send_events_when_frames_are_manipulated_dynamically(
    page, server, utils
):
    await page.goto(server.EMPTY_PAGE)
    # validate frameattached events
    attached_frames = []
    page.on("frameattached", lambda frame: attached_frames.append(frame))
    await utils.attach_frame(page, "frame1", "./assets/frame.html")
    assert len(attached_frames) == 1
    assert "/assets/frame.html" in attached_frames[0].url

    # validate framenavigated events
    navigated_frames = []
    page.on("framenavigated", lambda frame: navigated_frames.append(frame))
    await page.evaluate(
        """() => {
            frame = document.getElementById('frame1')
            frame.src = './empty.html'
            return new Promise(x => frame.onload = x)
        }"""
    )

    assert len(navigated_frames) == 1
    assert navigated_frames[0].url == server.EMPTY_PAGE

    # validate framedetached events
    detached_frames = list()
    page.on("framedetached", lambda frame: detached_frames.append(frame))
    await utils.detach_frame(page, "frame1")
    assert len(detached_frames) == 1
    assert detached_frames[0].is_detached()


async def test_framenavigated_when_navigating_on_anchor_urls(page, server):
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("framenavigated"):
        await page.goto(server.EMPTY_PAGE + "#foo")
    assert page.url == server.EMPTY_PAGE + "#foo"


async def test_persist_main_frame_on_cross_process_navigation(page, server):
    await page.goto(server.EMPTY_PAGE)
    main_frame = page.main_frame
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert page.main_frame == main_frame


async def test_should_not_send_attach_detach_events_for_main_frame(page, server):
    has_events = list()
    page.on("frameattached", lambda frame: has_events.append(True))
    page.on("framedetached", lambda frame: has_events.append(True))
    await page.goto(server.EMPTY_PAGE)
    assert has_events == []


async def test_detach_child_frames_on_navigation(page, server):
    attached_frames = []
    detached_frames = []
    navigated_frames = []
    page.on("frameattached", lambda frame: attached_frames.append(frame))
    page.on("framedetached", lambda frame: detached_frames.append(frame))
    page.on("framenavigated", lambda frame: navigated_frames.append(frame))
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    assert len(attached_frames) == 4
    assert len(detached_frames) == 0
    assert len(navigated_frames) == 5

    attached_frames = []
    detached_frames = []
    navigated_frames = []
    await page.goto(server.EMPTY_PAGE)
    assert len(attached_frames) == 0
    assert len(detached_frames) == 4
    assert len(navigated_frames) == 1


async def test_framesets(page, server):
    attached_frames = []
    detached_frames = []
    navigated_frames = []
    page.on("frameattached", lambda frame: attached_frames.append(frame))
    page.on("framedetached", lambda frame: detached_frames.append(frame))
    page.on("framenavigated", lambda frame: navigated_frames.append(frame))
    await page.goto(server.PREFIX + "/frames/frameset.html")
    assert len(attached_frames) == 4
    assert len(detached_frames) == 0
    assert len(navigated_frames) == 5

    attached_frames = []
    detached_frames = []
    navigated_frames = []
    await page.goto(server.EMPTY_PAGE)
    assert len(attached_frames) == 0
    assert len(detached_frames) == 4
    assert len(navigated_frames) == 1


async def test_frame_from_inside_shadow_dom(page, server):
    await page.goto(server.PREFIX + "/shadow.html")
    await page.evaluate(
        """async url => {
            frame = document.createElement('iframe');
            frame.src = url;
            document.body.shadowRoot.appendChild(frame);
            await new Promise(x => frame.onload = x);
        }""",
        server.EMPTY_PAGE,
    )
    assert len(page.frames) == 2
    assert page.frames[1].url == server.EMPTY_PAGE


async def test_frame_name(page, server, utils):
    await utils.attach_frame(page, "theFrameId", server.EMPTY_PAGE)
    await page.evaluate(
        """url => {
            frame = document.createElement('iframe');
            frame.name = 'theFrameName';
            frame.src = url;
            document.body.appendChild(frame);
            return new Promise(x => frame.onload = x);
        }""",
        server.EMPTY_PAGE,
    )
    assert page.frames[0].name == ""
    assert page.frames[1].name == "theFrameId"
    assert page.frames[2].name == "theFrameName"


async def test_frame_parent(page, server, utils):
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    assert page.frames[0].parent_frame is None
    assert page.frames[1].parent_frame == page.main_frame
    assert page.frames[2].parent_frame == page.main_frame


async def test_should_report_different_frame_instance_when_frame_re_attaches(
    page, server, utils
):
    frame1 = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
            window.frame = document.querySelector('#frame1')
            window.frame.remove()
        }"""
    )

    assert frame1.is_detached()
    async with page.expect_event("frameattached") as frame2_info:
        await page.evaluate("() => document.body.appendChild(window.frame)")

    frame2 = await frame2_info.value
    assert frame2.is_detached() is False
    assert frame1 != frame2
