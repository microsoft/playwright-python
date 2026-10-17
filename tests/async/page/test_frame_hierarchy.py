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

"""Port of tests/page/frame-hierarchy.spec.ts."""

import functools
import re
from typing import List

import pytest

from playwright.async_api import Frame, Page
from tests.server import Server, TestServerRequest

from ..utils import Utils


def dump_frames(frame: Frame, indentation: str = "") -> List[str]:
    description = frame.url
    if frame.name:
        description += " (" + frame.name + ")"
    result = [indentation + description]

    def compare(a: Frame, b: Frame) -> int:
        if a.url != b.url:
            return -1 if a.url < b.url else 1
        return -1 if a.name < b.name else 1

    child_frames = sorted(frame.child_frames, key=functools.cmp_to_key(compare))
    for child in child_frames:
        result.extend(dump_frames(child, "    " + indentation))
    return result


async def test_FR_024_should_handle_nested_frames_smoke(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    assert dump_frames(page.main_frame) == [
        f"{server.PREFIX}/frames/nested-frames.html",
        f"    {server.PREFIX}/frames/frame.html (aframe)",
        f"    {server.PREFIX}/frames/two-frames.html (2frames)",
        f"        {server.PREFIX}/frames/frame.html (dos)",
        f"        {server.PREFIX}/frames/frame.html (uno)",
    ]


async def test_FR_025_should_send_events_when_frames_are_manipulated_dynamically(
    page: Page, server: Server, utils: Utils
) -> None:
    await page.goto(server.EMPTY_PAGE)
    # validate frameattached events
    attached_frames: List[Frame] = []
    page.on("frameattached", lambda frame: attached_frames.append(frame))
    await utils.attach_frame(page, "frame1", "./assets/frame.html")
    assert len(attached_frames) == 1
    assert "/assets/frame.html" in attached_frames[0].url

    # validate framenavigated events
    navigated_frames: List[Frame] = []
    page.on("framenavigated", lambda frame: navigated_frames.append(frame))
    await page.evaluate(
        """() => {
        const frame = document.getElementById('frame1');
        frame.src = './empty.html';
        return new Promise(x => frame.onload = x);
    }"""
    )
    assert len(navigated_frames) == 1
    assert navigated_frames[0].url == server.EMPTY_PAGE

    # validate framedetached events
    detached_frames: List[Frame] = []
    page.on("framedetached", lambda frame: detached_frames.append(frame))
    await utils.detach_frame(page, "frame1")
    assert len(detached_frames) == 1
    assert detached_frames[0].is_detached() is True


async def test_FR_026_should_send_framenavigated_when_navigating_on_anchor_ur_ls(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_event("framenavigated"):
        await page.goto(server.EMPTY_PAGE + "#foo")
    assert page.url == server.EMPTY_PAGE + "#foo"


async def test_FR_027_should_persist_main_frame_on_cross_process_navigation(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    main_frame = page.main_frame
    await page.goto(server.CROSS_PROCESS_PREFIX + "/empty.html")
    assert page.main_frame == main_frame


async def test_FR_028_should_not_send_attach_detach_events_for_main_frame(
    page: Page, server: Server
) -> None:
    has_events: List[bool] = []
    page.on("frameattached", lambda frame: has_events.append(True))
    page.on("framedetached", lambda frame: has_events.append(True))
    await page.goto(server.EMPTY_PAGE)
    assert has_events == []


async def test_FR_029_should_detach_child_frames_on_navigation(
    page: Page, server: Server
) -> None:
    attached_frames: List[Frame] = []
    detached_frames: List[Frame] = []
    navigated_frames: List[Frame] = []
    page.on("frameattached", lambda frame: attached_frames.append(frame))
    page.on("framedetached", lambda frame: detached_frames.append(frame))
    page.on("framenavigated", lambda frame: navigated_frames.append(frame))
    await page.goto(server.PREFIX + "/frames/nested-frames.html")
    assert len(attached_frames) == 4
    assert len(detached_frames) == 0
    assert len(navigated_frames) == 5

    attached_frames.clear()
    detached_frames.clear()
    navigated_frames.clear()
    await page.goto(server.EMPTY_PAGE)
    assert len(attached_frames) == 0
    assert len(detached_frames) == 4
    assert len(navigated_frames) == 1


async def test_FR_030_should_support_framesets(page: Page, server: Server) -> None:
    attached_frames: List[Frame] = []
    detached_frames: List[Frame] = []
    navigated_frames: List[Frame] = []
    page.on("frameattached", lambda frame: attached_frames.append(frame))
    page.on("framedetached", lambda frame: detached_frames.append(frame))
    page.on("framenavigated", lambda frame: navigated_frames.append(frame))
    await page.goto(server.PREFIX + "/frames/frameset.html")
    assert len(attached_frames) == 4
    assert len(detached_frames) == 0
    assert len(navigated_frames) == 5

    attached_frames.clear()
    detached_frames.clear()
    navigated_frames.clear()
    await page.goto(server.EMPTY_PAGE)
    assert len(attached_frames) == 0
    assert len(detached_frames) == 4
    assert len(navigated_frames) == 1


async def test_FR_031_should_report_frame_from_inside_shadow_dom(
    page: Page, server: Server
) -> None:
    await page.goto(server.PREFIX + "/shadow.html")
    await page.evaluate(
        """async url => {
        const frame = document.createElement('iframe');
        frame.src = url;
        document.body.shadowRoot.appendChild(frame);
        await new Promise(x => frame.onload = x);
    }""",
        server.EMPTY_PAGE,
    )
    assert len(page.frames) == 2
    assert page.frames[1].url == server.EMPTY_PAGE


async def test_FR_032_should_report_frame_name(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "theFrameId", server.EMPTY_PAGE)
    await page.evaluate(
        """url => {
        const frame = document.createElement('iframe');
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


async def test_FR_033_should_report_frame_parent(
    page: Page, server: Server, utils: Utils
) -> None:
    await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await utils.attach_frame(page, "frame2", server.EMPTY_PAGE)
    assert page.frames[0].parent_frame is None
    assert page.frames[1].parent_frame == page.main_frame
    assert page.frames[2].parent_frame == page.main_frame


async def test_FR_034_should_report_different_frame_instance_when_frame_re_attaches(
    page: Page, server: Server, utils: Utils
) -> None:
    frame1 = await utils.attach_frame(page, "frame1", server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
        window['frame'] = document.querySelector('#frame1');
        window['frame'].remove();
    }"""
    )
    assert frame1.is_detached() is True
    async with page.expect_event("frameattached") as frame_info:
        await page.evaluate("() => document.body.appendChild(window['frame'])")
    frame2 = await frame_info.value
    assert frame2.is_detached() is False
    assert frame1 != frame2


@pytest.mark.skip_browser("firefox")
async def test_FR_035_should_refuse_to_display_x_frame_options_deny_iframe(
    page: Page, server: Server
) -> None:
    def handle(request: TestServerRequest) -> None:
        request.setHeader("Content-Type", "text/html")
        request.setHeader("X-Frame-Options", "DENY")
        request.write(
            b'<!DOCTYPE html><html><head><title>login</title></head><body style="background-color: red;"><p>dangerous login page</p></body></html>'
        )
        request.finish()

    server.set_route("/x-frame-options-deny.html", handle)
    await page.goto(server.EMPTY_PAGE)
    async with page.expect_console_message(
        lambda msg: bool(re.search(r"Refused to display", msg.text, re.IGNORECASE))
    ) as message_info:
        await page.set_content(
            f'<iframe src="{server.CROSS_PROCESS_PREFIX}/x-frame-options-deny.html"></iframe>'
        )
    refusal_text = (await message_info.value).text
    assert re.search(
        r"Refused to display .* in a frame because it set 'X-Frame-Options' to 'deny'.",
        refusal_text,
        re.IGNORECASE,
    )


async def test_FR_036_should_return_frame_page(page: Page, server: Server) -> None:
    await page.goto(server.PREFIX + "/frames/one-frame.html")
    assert page.main_frame.page == page
    assert page.main_frame.child_frames[0].page == page
