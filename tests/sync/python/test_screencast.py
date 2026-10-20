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


from playwright.sync_api import Page
from tests.server import Server


def ensure_some_frames(page: Page) -> None:
    for _ in range(100):
        page.evaluate(
            "() => new Promise(f => requestAnimationFrame(() => requestAnimationFrame(f)))"
        )
    page.screenshot()


def test_should_acknowledge_frames_after_callback(page: Page, server: Server) -> None:
    frame_count = 0

    def on_frame(_: object) -> None:
        nonlocal frame_count
        frame_count += 1
        assert page.title() == ""

    page.screencast.start(on_frame=on_frame)
    try:
        page.goto(server.EMPTY_PAGE)
        page.evaluate("() => document.body.style.backgroundColor = 'red'")
        ensure_some_frames(page)
        frames_before_repaint = frame_count
        page.evaluate("() => document.body.style.backgroundColor = 'blue'")
        ensure_some_frames(page)
        assert frame_count > frames_before_repaint
    finally:
        page.screencast.stop()


def test_should_report_callback_errors_and_continue_delivering_frames(
    page: Page, server: Server
) -> None:
    page.goto(server.EMPTY_PAGE)
    page.evaluate(
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

    def on_frame(_: object) -> None:
        nonlocal callback_count
        callback_count += 1
        raise RuntimeError("screencast callback failed")

    page.screencast.start(on_frame=on_frame)
    try:
        callback_error = None
        for _ in range(100):
            try:
                page.wait_for_timeout(100)
            except RuntimeError as error:
                callback_error = error
            if callback_error and callback_count > 1:
                break
        assert callback_error
        assert "screencast callback failed" in str(callback_error)
        assert callback_count > 1
    finally:
        try:
            page.screencast.stop()
        except RuntimeError as error:
            assert "screencast callback failed" in str(error)
            page.screencast.stop()
