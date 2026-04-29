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

import time

import pytest

from playwright.sync_api import Page
from tests.server import Server


def test_should_expose_screencast_property(page: Page) -> None:
    assert page.screencast is page.screencast


def test_start_should_deliver_frames_via_callback(page: Page, server: Server) -> None:
    received: list = []
    page.screencast.start(on_frame=lambda f: received.append(f["data"]))
    page.goto(server.EMPTY_PAGE)
    page.evaluate("() => document.body.style.backgroundColor = 'red'")
    # Force a couple of paint cycles so engines that only emit on visual change
    # still produce a frame. Mirrors upstream `ensureSomeFrames`.
    for _ in range(3):
        page.evaluate(
            "() => new Promise(f => requestAnimationFrame(() => requestAnimationFrame(f)))"
        )
    page.screenshot()
    deadline = time.time() + 10
    while not received and time.time() < deadline:
        page.wait_for_timeout(100)
    page.screencast.stop()
    assert len(received) >= 1
    assert all(isinstance(d, bytes) and len(d) > 0 for d in received)


def test_starting_twice_should_throw(page: Page) -> None:
    page.screencast.start(on_frame=lambda f: None)
    try:
        with pytest.raises(Exception, match="already started"):
            page.screencast.start(on_frame=lambda f: None)
    finally:
        page.screencast.stop()
