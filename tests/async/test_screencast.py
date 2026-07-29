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
import time

import pytest

from playwright.async_api import Browser, Page, ScreencastFrame, ScreencastSize
from tests.server import Server


async def test_should_expose_screencast_property(page: Page) -> None:
    assert page.screencast is page.screencast


async def test_start_should_deliver_frames_via_callback(
    page: Page, server: Server
) -> None:
    received: list = []
    event = asyncio.Event()

    def on_frame(frame: ScreencastFrame) -> None:
        received.append(frame["data"])
        event.set()

    await page.screencast.start(on_frame=on_frame)
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate("() => document.body.style.backgroundColor = 'red'")
    # Force a couple of paint cycles so engines that only emit on visual change
    # still produce a frame. Mirrors upstream `ensureSomeFrames`.
    for _ in range(3):
        await page.evaluate(
            "() => new Promise(f => requestAnimationFrame(() => requestAnimationFrame(f)))"
        )
    await page.screenshot()
    await asyncio.wait_for(event.wait(), timeout=10)
    await page.screencast.stop()
    assert len(received) >= 1
    assert all(isinstance(d, bytes) and len(d) > 0 for d in received)


async def test_start_should_apply_backpressure_while_async_callback_is_pending(
    page: Page, server: Server
) -> None:
    release_callback = asyncio.Event()
    first_frame_received = asyncio.Event()
    next_frame_received = asyncio.Event()
    frame_count = 0
    frames_while_blocked = None
    last_frame_time = 0.0

    async def on_frame(frame: ScreencastFrame) -> None:
        nonlocal frame_count, last_frame_time
        frame_count += 1
        last_frame_time = time.monotonic()
        first_frame_received.set()
        if frames_while_blocked is not None and frame_count > frames_while_blocked:
            next_frame_received.set()
        await release_callback.wait()

    await page.screencast.start(on_frame=on_frame)
    try:
        await page.goto(server.EMPTY_PAGE)
        await page.evaluate(
            """() => {
                const animate = () => {
                    document.body.style.backgroundColor = document.body.style.backgroundColor === 'red' ? 'blue' : 'red';
                    requestAnimationFrame(animate);
                };
                requestAnimationFrame(animate);
            }"""
        )
        await asyncio.wait_for(first_frame_received.wait(), timeout=10)
        while time.monotonic() - last_frame_time <= 1:
            await asyncio.sleep(0.1)
        frames_while_blocked = frame_count
        await page.evaluate(
            "() => document.body.style.backgroundColor = document.body.style.backgroundColor === 'red' ? 'blue' : 'red'"
        )
        await asyncio.sleep(1)
        assert frame_count == frames_while_blocked
        release_callback.set()
        await asyncio.wait_for(next_frame_received.wait(), timeout=10)
    finally:
        release_callback.set()
        await page.screencast.stop()


async def test_starting_twice_should_throw(page: Page) -> None:
    await page.screencast.start(on_frame=lambda f: None)
    try:
        with pytest.raises(Exception, match="already started"):
            await page.screencast.start(on_frame=lambda f: None)
    finally:
        await page.screencast.stop()


async def test_show_overlays_and_overlay_apis_should_not_throw(page: Page) -> None:
    await page.screencast.start(on_frame=lambda f: None)
    try:
        await page.screencast.show_overlay("<div>hello</div>", duration=100)
        await page.screencast.show_chapter("ch", description="desc", duration=100)
        await page.screencast.hide_overlays()
        await page.screencast.show_overlays()
        await page.screencast.show_actions(duration=100, position="top-right")
        await page.screencast.hide_actions()
    finally:
        await page.screencast.stop()


async def test_on_frame_receives_viewport_size(
    browser: Browser, server: Server
) -> None:
    context = await browser.new_context(viewport={"width": 1000, "height": 400})
    async with context:
        page = await context.new_page()
        received: list = []

        def on_frame(frame: ScreencastFrame) -> None:
            received.append(frame)

        size: ScreencastSize = {"width": 500, "height": 400}
        await page.screencast.start(on_frame=on_frame, size=size)
        await page.goto(server.EMPTY_PAGE)
        await page.evaluate("() => document.body.style.backgroundColor = 'red'")
        for _ in range(100):
            await page.evaluate(
                "() => new Promise(f => requestAnimationFrame(() => requestAnimationFrame(f)))"
            )
        await page.screenshot()
        await page.screencast.stop()
        assert len(received) >= 1
        assert any(frame["viewportWidth"] == 1000 for frame in received)
        for frame in received:
            assert frame["viewportHeight"] == 400
            assert isinstance(frame["timestamp"], (int, float))


async def test_show_actions_should_accept_cursor_param(page: Page) -> None:
    await page.screencast.start(on_frame=lambda f: None)
    try:
        async with await page.screencast.show_actions(duration=100, cursor="pointer"):
            pass
        async with await page.screencast.show_actions(duration=100, cursor="none"):
            pass
    finally:
        await page.screencast.stop()
