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

from playwright.sync_api import BrowserContext, Page


def test_should_return_none_paused_details_initially(
    context: BrowserContext,
) -> None:
    dbg = context.debugger
    assert dbg.paused_details is None


def test_should_pause_at_next_and_resume(page: Page, context: BrowserContext) -> None:
    page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    dbg.request_pause()

    handler_called = [0]

    def on_paused_state_changed() -> None:
        handler_called[0] += 1
        if dbg.paused_details is not None:
            assert "Click" in dbg.paused_details["title"]
            dbg.resume()

    dbg.on("pausedstatechanged", on_paused_state_changed)

    page.click("div")
    assert dbg.paused_details is None
    assert handler_called[0] > 0


def test_should_step_with_next(page: Page, context: BrowserContext) -> None:
    page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    dbg.request_pause()

    first_pause_seen = [False]
    handler_called = [0]

    def on_paused_state_changed() -> None:
        handler_called[0] += 1
        if dbg.paused_details is not None and not first_pause_seen[0]:
            assert "Click" in dbg.paused_details["title"]
            first_pause_seen[0] = True
            dbg.next()
        elif dbg.paused_details is not None and first_pause_seen[0]:
            dbg.resume()

    dbg.on("pausedstatechanged", on_paused_state_changed)

    page.click("div")
    assert dbg.paused_details is None
    assert handler_called[0] > 0


def test_should_pause_at_pause_call(page: Page, context: BrowserContext) -> None:
    page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    dbg.request_pause()

    handler_called = [0]

    def on_paused_state_changed() -> None:
        handler_called[0] += 1
        if dbg.paused_details is not None:
            assert "Pause" in dbg.paused_details["title"]
            dbg.resume()

    dbg.on("pausedstatechanged", on_paused_state_changed)

    page.pause()
    assert dbg.paused_details is None
    assert handler_called[0] > 0
