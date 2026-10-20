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

"""Python only: tests of behaviors that no upstream test covers."""


from playwright.async_api import Page, ScreencastFrame
from tests.server import Server


async def test_should_expose_screencast_property(page: Page) -> None:
    assert page.screencast is page.screencast


async def test_should_report_callback_errors_and_continue_delivering_frames(
    page: Page, server: Server
) -> None:
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """() => {
            const animate = () => {
                document.body.style.backgroundColor =
                    document.body.style.backgroundColor === "red" ? "blue" : "red";
                requestAnimationFrame(animate);
            };
            requestAnimationFrame(animate);
        }"""
    )
    callback_count = 0

    async def on_frame(_: ScreencastFrame) -> None:
        nonlocal callback_count
        callback_count += 1
        raise RuntimeError("screencast callback failed")

    await page.screencast.start(on_frame=on_frame)
    try:
        callback_error = None
        for _ in range(100):
            try:
                await page.wait_for_timeout(100)
            except RuntimeError as error:
                callback_error = error
            if callback_error and callback_count > 1:
                break
        assert callback_error
        assert "screencast callback failed" in str(callback_error)
        assert callback_count > 1
    finally:
        try:
            await page.screencast.stop()
        except RuntimeError as error:
            assert "screencast callback failed" in str(error)
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
