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

"""Port of tests/library/debugger.spec.ts.

Upstream starts the action without awaiting it, waits for 'pausedstatechanged' and
resumes from the test body. Here the test body awaits the action, and a
'pausedstatechanged' listener resumes the debugger: an action that runs in its own
asyncio task reports the asyncio frame as its location, not the test file.
"""

from pathlib import Path
from typing import Any, List, Optional

from playwright._impl_v2.channel_owner import ApiCallOptions
from playwright.async_api import BrowserContext, DebuggerPausedDetails
from tests.server import Server


def record_paused_states(
    context: BrowserContext,
) -> List[Optional[DebuggerPausedDetails]]:
    """Returns a list that gets debugger.paused_details at each 'pausedstatechanged'."""
    dbg = context.debugger
    states: List[Optional[DebuggerPausedDetails]] = []
    dbg.on("pausedstatechanged", lambda: states.append(dbg.paused_details))
    return states


def resume_when_paused(context: BrowserContext) -> None:
    """Resumes the debugger at the next 'pausedstatechanged'."""
    dbg = context.debugger

    async def resume() -> None:
        await dbg.resume()

    dbg.once("pausedstatechanged", resume)


def line_of(marker: str) -> int:
    """The number of the line in this file that ends with the marker comment."""
    lines = Path(__file__).read_text().splitlines()
    return next(
        index + 1 for index, text in enumerate(lines) if text.rstrip().endswith(marker)
    )


async def test_DB_001_should_pause_at_next_and_resume(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    await dbg.request_pause()
    states = record_paused_states(context)
    resume_when_paused(context)
    await page.click("div")

    assert len(states) == 2
    paused_details = states[0]
    assert paused_details is not None
    assert "Click" in paused_details["title"]
    location = paused_details["location"]
    assert "test_debugger" in location["file"]
    assert isinstance(location["line"], int)
    assert isinstance(location["column"], int)

    assert states[1] is None
    assert dbg.paused_details is None


async def test_DB_002_should_pause_at_pause_call(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    await dbg.request_pause()
    states = record_paused_states(context)
    resume_when_paused(context)
    await page.pause()

    paused_details = states[0]
    assert paused_details is not None
    assert "Pause" in paused_details["title"]


async def test_DB_003_should_run_to_location(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.set_content("<div>click me</div>")
    dbg = context.debugger
    assert dbg.paused_details is None

    # First, pause on next action.
    await dbg.request_pause()
    states = record_paused_states(context)

    async def run_to_location() -> None:
        # Now run to a specific location.
        line = line_of("# should pause here")
        await dbg.run_to({"file": "test_debugger.py", "line": line, "column": None})

    dbg.once("pausedstatechanged", run_to_location)
    await page.click("div")
    assert len(states) == 2

    await page.content()  # should not pause here
    assert len(states) == 2
    resume_when_paused(context)
    await page.click("div")  # should pause here

    assert len(states) == 4
    paused_details = states[2]
    assert paused_details is not None
    assert "Click" in paused_details["title"]


async def test_DB_007_should_not_pause_at_internal_api_calls(
    context: BrowserContext, server: Server
) -> None:
    page = await context.new_page()
    await page.set_content("<button>click me</button>")
    dbg = context.debugger

    await dbg.request_pause()
    # The internal call must not trip the pause, and must not consume the arming.
    # Port of `page._wrapApiCall(() => page.click('button'), { internal: true })`.
    # Python: _impl_obj is typed as the v1 Page; under PW_IMPL=v2 it is the v2 one.
    impl: Any = page._impl_obj
    await impl._wrap_api_call(
        lambda _: page.click("button"), ApiCallOptions(internal=True)
    )
    assert dbg.paused_details is None

    # The next normal call still pauses.
    states = record_paused_states(context)
    resume_when_paused(context)
    await page.click("button")
    assert states[0]
    assert len(states) == 2
