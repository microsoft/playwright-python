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

"""Port of tests/library/tracing.spec.ts."""

import asyncio
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import pytest
from PIL import Image
from twisted.internet.task import LoopingCall

from playwright.async_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Dialog,
    Error,
    Page,
    Playwright,
    expect,
)
from tests.helpers.trace_parser import parse_trace_raw
from tests.server import Server, WebSocketProtocol

from ..utils import Utils


async def run_in_background(
    page: Page, action: Callable[[], Awaitable[Any]]
) -> "asyncio.Future[Any]":
    """Like calling an async function without await: starts the action and goes on.

    The future settles with the result or the error of the action. The page is not used
    here; the sync flavor takes the event loop from it.
    """

    async def run() -> Any:
        try:
            return await action()
        except Exception as error:
            return error

    task = asyncio.ensure_future(run())
    # Let the action send its message, as the JavaScript call does before it returns.
    await asyncio.sleep(0)
    return task


async def sleep(page: Page, ms: float) -> None:
    """Like `await new Promise(f => setTimeout(f, ms))`: no message to the driver."""
    await asyncio.sleep(ms / 1000)


async def to_pass(page: Page, check: Callable[[], None], timeout: float = 5000) -> None:
    """Like `await expect(async () => { ... }).toPass()`: retries the check until it passes."""
    deadline = asyncio.get_running_loop().time() + timeout / 1000
    while True:
        try:
            check()
            return
        except (AssertionError, OSError, StopIteration):
            if asyncio.get_running_loop().time() > deadline:
                raise
        await sleep(page, 100)


def relative_stack(
    action: Dict[str, Any], stacks: Dict[str, List[Dict[str, Any]]]
) -> List[str]:
    stack = stacks.get(action["callId"]) or []
    return [f["file"].replace(str(Path(__file__).parent) + os.sep, "") for f in stack]


def resource_snapshot(events: List[Dict[str, Any]], suffix: str) -> Optional[Dict]:
    return next(
        (
            e
            for e in events
            if e["type"] == "resource-snapshot"
            and e["snapshot"]["request"]["url"].endswith(suffix)
        ),
        None,
    )


def expect_red(pixels: bytes, offset: int) -> None:
    r, g, b, a = (
        pixels[offset],
        pixels[offset + 1],
        pixels[offset + 2],
        pixels[offset + 3],
    )
    assert r > 200
    assert g < 70
    assert b < 70
    assert a == 255


def expect_blue(pixels: bytes, offset: int) -> None:
    r, g, b, a = (
        pixels[offset],
        pixels[offset + 1],
        pixels[offset + 2],
        pixels[offset + 3],
    )
    assert r < 70
    assert g < 70
    assert b > 200
    assert a == 255


def decode_image(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as image:
        return image.convert("RGBA")


async def test_TR_001_should_collect_trace_with_resources_but_no_js(
    context: BrowserContext,
    page: Page,
    server: Server,
    assetdir: Path,
    tmp_path: Path,
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.PREFIX + "/frames/frame.html")
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await page.mouse.move(20, 20)
    await page.mouse.dblclick(30, 30)
    await page.keyboard.insert_text("abc")
    await page.goto(server.PREFIX + "/input/fileupload.html")
    await page.locator('input[type="file"]').set_input_files(
        assetdir / "file-to-upload.txt"
    )
    await page.wait_for_timeout(2000)  # Give it some time to produce screenshots.
    await page.close()
    await context.tracing.stop(path=tmp_path / "trace.zip")

    trace = parse_trace_raw(tmp_path / "trace.zip")
    events = trace.events
    assert events[0]["type"] == "context-options"
    assert trace.actions == [
        f"Navigate {server.HOST}/frames/frame.html",
        "Set content",
        """Click locator('text="Click"')""",
        "Mouse move",
        "Double click",
        'Insert "abc"',
        f"Navigate {server.HOST}/input/fileupload.html",
        """Set input files locator('input[type="file"]')""",
        "Wait for timeout",
        "Close page",
    ]

    assert any(e["type"] == "frame-snapshot" for e in events)
    assert any(e["type"] == "screencast-frame" for e in events)
    style = resource_snapshot(events, "style.css")
    assert style
    assert style["snapshot"]["response"]["content"]["_file"]
    script = resource_snapshot(events, "script.js")
    assert script
    assert "_file" not in script["snapshot"]["response"]["content"]


async def test_TR_002_should_use_the_correct_title_for_event_driven_callbacks(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start()
    # route.* calls should not be included in the trace
    await page.route("**/empty.html", lambda route: route.continue_())
    await page.goto(server.PREFIX + "/empty.html")
    await page.goto(server.PREFIX + "/grid.html")

    # The default internal dialog handler should not provide an action.
    await page.evaluate("() => alert('yo')")
    await page.reload()
    # now we do it again with a dialog event listener attached which should produce an action.
    page.on("dialog", lambda dialog: dialog.accept("answer!"))
    await page.evaluate("() => alert('yo')")

    await context.tracing.stop(path=tmp_path / "trace.zip")
    trace = parse_trace_raw(tmp_path / "trace.zip")
    assert trace.events[0]["type"] == "context-options"
    assert trace.actions == [
        "Route requests",
        f"Navigate {server.HOST}/empty.html",
        "Continue request",
        f"Navigate {server.HOST}/grid.html",
        "Evaluate",
        "Reload",
        "Evaluate",
        "Accept dialog",
    ]


async def test_TR_003_should_not_store_secrets_in_context_options(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = await browser.new_context(
        base_url=server.PREFIX,
        viewport={"width": 500, "height": 600},
        device_scale_factor=2,
        is_mobile=False,
        user_agent="custom-ua",
        http_credentials={"username": "user", "password": "secret-password"},
        extra_http_headers={"x-secret": "secret-header"},
        storage_state={
            "cookies": [
                {
                    "name": "session",
                    "value": "secret-cookie",
                    "domain": "localhost",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "Lax",
                }
            ],
            "origins": [],
        },
    )
    await context.tracing.start()
    page = await context.new_page()
    await page.goto(server.EMPTY_PAGE)
    await context.tracing.stop(path=tmp_path / "trace.zip")
    await context.close()

    events = parse_trace_raw(tmp_path / "trace.zip").events
    assert events[0]["type"] == "context-options"
    assert events[0]["options"] == {
        "baseURL": server.PREFIX,
        "viewport": {"width": 500, "height": 600},
        "deviceScaleFactor": 2,
        "isMobile": False,
        "userAgent": "custom-ua",
    }
    trace_text = (tmp_path / "trace.zip").read_bytes().decode("latin1")
    assert "secret-password" not in trace_text
    assert "secret-header" not in trace_text
    assert "secret-cookie" not in trace_text


async def test_TR_004_should_not_collect_snapshots_by_default(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await page.close()
    await context.tracing.stop(path=tmp_path / "trace.zip")

    events = parse_trace_raw(tmp_path / "trace.zip").events
    assert not any(e["type"] == "frame-snapshot" for e in events)
    assert not any(e["type"] == "resource-snapshot" for e in events)


async def test_TR_005_should_not_collect_action_screenshots_and_aria_snapshots_by_default(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(snapshots=True)
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await context.tracing.stop(path=tmp_path / "trace.zip")

    events = parse_trace_raw(tmp_path / "trace.zip").events
    assert not any(e["type"] == "screenshot" for e in events)
    assert not any(e["type"] == "aria-snapshot" for e in events)


async def test_TR_006_should_collect_action_screenshots(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(screen_snapshots=True)
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await context.tracing.stop(path=tmp_path / "trace.zip")

    trace = parse_trace_raw(tmp_path / "trace.zip")
    click_call_id = next(
        e for e in trace.events if e["type"] == "before" and e.get("method") == "click"
    )["callId"]
    screenshots = [
        e
        for e in trace.events
        if e["type"] == "screenshot" and e["callId"] == click_call_id
    ]
    assert [e["phase"] for e in screenshots] == ["before", "action", "after"]
    for screenshot in screenshots:
        assert (
            screenshot["file"]
            == f"screenshots/{click_call_id}-{screenshot['phase']}.png"
        )
        buffer = trace.resources[screenshot["file"]]
        assert decode_image(buffer).width > 0


async def test_TR_007_should_collect_aria_snapshots(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(aria_snapshots=True)
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await context.tracing.stop(path=tmp_path / "trace.zip")

    trace = parse_trace_raw(tmp_path / "trace.zip")
    click_call_id = next(
        e for e in trace.events if e["type"] == "before" and e.get("method") == "click"
    )["callId"]
    aria_snapshots = [
        e
        for e in trace.events
        if e["type"] == "aria-snapshot" and e["callId"] == click_call_id
    ]
    assert [e["phase"] for e in aria_snapshots] == ["before", "action", "after"]

    def has_button(nodes: List[Any]) -> bool:
        return any(
            isinstance(node, dict)
            and (
                (node.get("role") == "button" and node.get("name") == "Click target")
                or has_button(node.get("children") or [])
            )
            for node in nodes
        )

    for aria_snapshot in aria_snapshots:
        assert (
            aria_snapshot["file"]
            == f"aria/{click_call_id}-{aria_snapshot['phase']}.json"
        )
        snapshot = json.loads(trace.resources[aria_snapshot["file"]])
        assert has_button(snapshot) is True


async def test_TR_008_can_call_tracing_group_group_end_at_any_time_and_auto_close(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.group("ignored")
    await context.tracing.group_end()
    await context.tracing.group("ignored2")

    await context.tracing.start()
    await context.tracing.group("actual")
    await page.goto(server.EMPTY_PAGE)
    await context.tracing.stop_chunk(path=tmp_path / "trace.zip")

    await context.tracing.group("ignored3")
    await context.tracing.group_end()
    await context.tracing.group_end()
    await context.tracing.group_end()

    events = parse_trace_raw(tmp_path / "trace.zip").events
    groups = [e for e in events if e.get("method") == "tracingGroup"]
    assert len(groups) == 1
    assert groups[0]["title"] == "actual"
    assert (
        any(e["type"] == "after" and e["callId"] == groups[0]["callId"] for e in events)
        is True
    )


async def test_TR_009_should_not_include_buffers_in_the_trace(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(snapshots=True)
    await page.goto(server.PREFIX + "/empty.html")
    await page.screenshot()
    await context.tracing.stop(path=tmp_path / "trace.zip")
    trace = parse_trace_raw(tmp_path / "trace.zip")
    screenshot_event = next(
        a for a in trace.action_objects if a["method"] == "screenshot"
    )
    phases = [
        e["snapshot"]["phase"]
        for e in trace.events
        if e["type"] == "frame-snapshot"
        and e["snapshot"]["callId"] == screenshot_event["callId"]
    ]
    assert "before" in phases
    assert "after" in phases
    assert screenshot_event["result"] == {
        "binary": "<Buffer>",
    }


async def test_TR_010_should_exclude_internal_pages(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.EMPTY_PAGE)

    await context.tracing.start()
    await context.storage_state()
    await page.close()
    await context.tracing.stop(path=tmp_path / "trace.zip")

    trace = parse_trace_raw(tmp_path / "trace.zip")
    page_ids = set()
    for e in trace.events:
        page_id = e.get("pageId") or (e.get("params") or {}).get("pageId")
        if page_id:
            page_ids.add(page_id)
    assert len(page_ids) == 1


@pytest.mark.xfail(
    reason="python: trace stacks keep the asyncio and pytest frames below the test (upstream keeps only the test's frames)",
    strict=True,
)
async def test_TR_011_should_record_context_api_request_trace_independently(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    browser_trace_path = tmp_path / "browser-trace.zip"
    api_trace_path = tmp_path / "api-trace.zip"
    api_url = server.PREFIX + "/simple.json"
    assert context.request.tracing != context.tracing

    await context.tracing.start(snapshots=True)
    await context.request.tracing.start(snapshots=True)
    await page.goto(server.PREFIX + "/one-style.html")
    await page.request.post(api_url, data={"foo": "bar"})
    await context.tracing.stop(path=browser_trace_path)
    await context.request.tracing.stop(path=api_trace_path)

    browser_trace = parse_trace_raw(browser_trace_path)
    assert f"Navigate {server.HOST}/one-style.html" in browser_trace.actions
    assert f"POST {server.HOST}/simple.json" not in browser_trace.actions
    assert (
        any(
            event["type"] == "resource-snapshot"
            and event["snapshot"]["request"]["url"].endswith("/simple.json")
            for event in browser_trace.events
        )
        is False
    )
    assert (
        any(
            event["type"] == "resource-snapshot"
            and event["snapshot"]["request"]["url"].endswith("/one-style.html")
            for event in browser_trace.events
        )
        is True
    )

    api_trace = parse_trace_raw(api_trace_path)
    assert f"POST {server.HOST}/simple.json" in api_trace.actions
    assert f"Navigate {server.HOST}/one-style.html" not in api_trace.actions
    api_action = next(
        action
        for action in api_trace.action_objects
        if action["class"] == "APIRequestContext" and action["method"] == "fetch"
    )
    assert relative_stack(api_action, api_trace.stacks) == ["test_tracing.py"]
    resource_snapshots = [
        event for event in api_trace.events if event["type"] == "resource-snapshot"
    ]
    assert [event["snapshot"]["request"]["url"] for event in resource_snapshots] == [
        api_url
    ]
    api_request_refs = [
        event["snapshot"]["_apiRequestRef"] for event in resource_snapshots
    ]
    assert len(api_request_refs) == 1
    assert re.match(r"^request-context@", api_request_refs[0])


async def test_TR_012_should_collect_two_traces(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await context.tracing.stop(path=tmp_path / "trace1.zip")

    await context.tracing.start(screenshots=True, snapshots=True)
    await page.dblclick('"Click"')
    await page.close()
    await context.tracing.stop(path=tmp_path / "trace2.zip")

    trace1 = parse_trace_raw(tmp_path / "trace1.zip")
    assert trace1.events[0]["type"] == "context-options"
    assert trace1.actions == [
        f"Navigate {server.HOST}/empty.html",
        "Set content",
        """Click locator('text="Click"')""",
    ]

    trace2 = parse_trace_raw(tmp_path / "trace2.zip")
    assert trace2.events[0]["type"] == "context-options"
    assert trace2.actions == [
        """Double click locator('text="Click"')""",
        "Close page",
    ]


async def test_TR_013_should_respect_traces_dir_and_name(
    browser_type: BrowserType, launch_arguments: Dict, server: Server, tmp_path: Path
) -> None:
    traces_dir = tmp_path / "traces"
    browser = await browser_type.launch(**launch_arguments, traces_dir=traces_dir)
    context = await browser.new_context()
    page = await context.new_page()

    await context.tracing.start(name="name1", snapshots=True)
    await page.goto(server.PREFIX + "/one-style.html")
    await context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert (traces_dir / "name1.trace").exists() is True
    assert (traces_dir / "name1.network").exists() is True

    await context.tracing.start_chunk(name="name2")
    await page.goto(server.PREFIX + "/har.html")
    await context.tracing.stop(path=tmp_path / "trace2.zip")
    assert (traces_dir / "name2.trace").exists() is True
    assert (traces_dir / "name2.network").exists() is True

    await browser.close()

    def resource_names(resources: Dict[str, bytes]) -> List[str]:
        return sorted(
            re.sub(r"^resources/.*\.(html|css)$", r"resources/XXX.\1", file)
            for file in resources
        )

    trace1 = parse_trace_raw(tmp_path / "trace1.zip")
    assert trace1.actions == [f"Navigate {server.HOST}/one-style.html"]
    assert resource_names(trace1.resources) == [
        "resources/XXX.css",
        "resources/XXX.html",
        "trace.network",
        "trace.stacks",
        "trace.trace",
    ]

    trace2 = parse_trace_raw(tmp_path / "trace2.zip")
    assert trace2.actions == [f"Navigate {server.HOST}/har.html"]
    assert resource_names(trace2.resources) == [
        "resources/XXX.css",
        "resources/XXX.html",
        "resources/XXX.html",
        "trace.network",
        "trace.stacks",
        "trace.trace",
    ]


@pytest.mark.xfail(
    reason="python: sources=True collects the asyncio and pytest files of the stacks too (upstream collects only the test file)",
    strict=True,
)
async def test_TR_014_should_not_include_trace_resources_from_the_previous_chunks(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)

    await context.tracing.start_chunk()
    await page.goto(server.EMPTY_PAGE)
    await page.set_content(
        """
    <style>
      @keyframes move {
        from { marign-left: 0; }
        to   { margin-left: 1000px; }
      }
      button {
        animation: 20s linear move;
        animation-iteration-count: infinite;
      }
    </style>
    <button>Click</button>
  """
    )
    await page.click('"Click"', force=True)
    # Give it enough time for both screenshots to get into the trace.
    await sleep(page, 3000)
    await context.tracing.stop_chunk(path=tmp_path / "trace1.zip")

    await context.tracing.start_chunk()
    await context.tracing.stop_chunk(path=tmp_path / "trace2.zip")

    names = list(parse_trace_raw(tmp_path / "trace1.zip").resources)
    assert len([n for n in names if n.endswith(".html")]) == 1
    jpegs = [n for n in names if n.endswith(".jpeg")]
    # 1 source file for the test.
    assert len([n for n in names if n.startswith("src/")]) == 1

    names = list(parse_trace_raw(tmp_path / "trace2.zip").resources)
    # 1 network resource should be preserved.
    assert len([n for n in names if n.endswith(".html")]) == 1
    # screenshots from the previous chunk should not be preserved.
    assert len([n for n in names if n in jpegs]) == 0
    # 0 source files for the second test.
    assert len([n for n in names if n.startswith("src/")]) == 0


async def test_TR_015_should_overwrite_existing_file(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    path = tmp_path / "trace1.zip"
    await context.tracing.stop(path=path)
    names = list(parse_trace_raw(path).resources)
    assert len([n for n in names if n.endswith(".html")]) == 1

    await context.tracing.start(screenshots=True, snapshots=True, sources=True)
    await context.tracing.stop(path=path)

    names = list(parse_trace_raw(path).resources)
    assert len([n for n in names if n.endswith(".html")]) == 0


@pytest.mark.xfail(
    reason="python: sources=True collects the asyncio and pytest files of the stacks too (upstream collects only the test file)",
    strict=True,
)
async def test_TR_016_should_collect_sources(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(sources=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await context.tracing.stop(path=tmp_path / "trace1.zip")

    resources = parse_trace_raw(tmp_path / "trace1.zip").resources
    source_names = [k for k in resources if k.startswith("src/")]
    assert len(source_names) == 1
    assert re.match(r"^src/[0-9a-f]{40}\.py$", source_names[0])
    source_file = resources[source_names[0]]
    this_file = Path(__file__).read_bytes()
    assert source_file == this_file


async def test_TR_017_should_record_network_failures(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(snapshots=True)
    await page.route("**/*", lambda route: route.abort("connectionaborted"))
    try:
        await page.goto(server.EMPTY_PAGE)
    except Error:
        pass
    await context.tracing.stop(path=tmp_path / "trace1.zip")

    events = parse_trace_raw(tmp_path / "trace1.zip").events
    request_event = next(
        (
            e
            for e in events
            if e["type"] == "resource-snapshot"
            and e["snapshot"]["response"].get("_failureText")
        ),
        None,
    )
    assert request_event
    assert request_event["snapshot"]["_monotonicTime"] > 0
    assert request_event["snapshot"]["time"] >= 0


@pytest.mark.xfail(
    reason="python: Tracing.stop() skips tracingStop when saving the chunk fails, so the next start() fails with 'Tracing has been already started'",
    strict=True,
)
async def test_TR_018_should_recover_tracing_after_a_failed_stop(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start()
    # Saving fails: a parent of the destination is a file, not a directory.
    blocker = tmp_path / "blocker"
    blocker.write_text("")
    with pytest.raises(Error, match=r"ENOTDIR|ENOENT|EEXIST"):
        await context.tracing.stop(path=blocker / "trace1.zip")

    # The failed stop must not wedge tracing for the rest of the context lifetime.
    await context.tracing.start()
    await page.goto(server.PREFIX + "/input/button.html")
    await page.click("button")
    await context.tracing.stop(path=tmp_path / "trace2.zip")

    trace = parse_trace_raw(tmp_path / "trace2.zip")
    assert trace.events[0]["type"] == "context-options"
    assert "Click locator('button')" in trace.actions


@pytest.mark.xfail(
    reason="python: Tracing._do_stop_chunk() does not call localUtils.traceDiscarded when saving the chunk fails, so the stack session's directory stays",
    strict=True,
)
async def test_TR_019_should_release_the_stack_session_when_saving_the_trace_fails(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    # Launch without tracesDir, so that the stack session owns a temporary directory.
    browser = await browser_type.launch(**launch_arguments)
    try:
        context = await browser.new_context()
        await context.tracing.start()
        stacks_id = context.tracing._impl_obj._stacks_id
        assert stacks_id
        stacks_dir = Path(stacks_id).parent
        assert stacks_dir.exists() is True

        blocker = tmp_path / "blocker"
        blocker.write_text("")
        with pytest.raises(Error, match=r"ENOTDIR|ENOENT|EEXIST"):
            await context.tracing.stop(path=blocker / "trace.zip")
        assert stacks_dir.exists() is False
    finally:
        await browser.close()


async def test_TR_020_should_not_crash_when_browser_closes_mid_trace(
    browser_type: BrowserType, launch_arguments: Dict, server: Server
) -> None:
    browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.context.tracing.start(snapshots=True, screenshots=True)
    await page.goto(server.EMPTY_PAGE)
    await browser.close()
    await sleep(page, 1000)  # Give it some time to throw errors


async def test_TR_021_should_survive_browser_close_with_auto_created_traces_dir(
    browser_type: BrowserType, launch_arguments: Dict
) -> None:
    # Python does not set a default tracesDir: the browser auto-creates one.
    browser = await browser_type.launch(**launch_arguments)
    page = await browser.new_page()
    await page.context.tracing.start()

    done = False

    async def go() -> None:
        while not done:
            # Produce a lot of operations to make sure tracing operations are enqueued.
            for _ in range(100):
                await run_in_background(page, lambda: page.evaluate("1 + 1"))
            await sleep(page, 250)

    await run_in_background(page, go)
    await sleep(page, 1000)

    # Close the browser and give it some time to fail.
    await asyncio.gather(browser.close(), sleep(page, 500))

    done = True


async def test_TR_022_should_not_stall_on_dialogs(
    page: Page, context: BrowserContext, server: Server
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)

    async def on_dialog(dialog: Dialog) -> None:
        await dialog.accept()

    page.on("dialog", on_dialog)

    await page.evaluate(
        """() => {
    confirm('are you sure');
  }"""
    )
    await context.tracing.stop()


@pytest.mark.parametrize(
    "id, width, height",
    [
        ("fit", 500, 500),
        ("crop", 400, 800),  # Less than 450 to test firefox
        ("scale", 1024, 768),
    ],
)
async def test_TR_023_should_produce_screencast_frames(
    context_factory: Callable[..., Awaitable[BrowserContext]],
    browser_name: str,
    platform: str,
    headless: bool,
    is_headless_shell: bool,
    utils: Utils,
    tmp_path: Path,
    id: str,
    width: int,
    height: int,
) -> None:
    if browser_name == "chromium" and not is_headless_shell:
        pytest.skip(
            "fixme: Chromium (but not headless-shell) screencast has a min width issue"
        )
    if id == "fit" and browser_name == "chromium" and platform == "darwin":
        pytest.skip("fixme: High DPI maxes image at 600x600")
    if id == "fit" and browser_name == "webkit" and platform == "linux":
        pytest.skip("fixme: Image size is flaky")
    if browser_name == "firefox" and not headless:
        pytest.skip("fixme: Image size is different")

    scale = min(800 / width, 800 / height, 1)
    preview_width = int(width * scale)
    preview_height = int(height * scale)

    context = await context_factory(viewport={"width": width, "height": height})
    await context.tracing.start(screenshots=True, snapshots=True)
    page = await context.new_page()
    # Make sure we have a chance to paint.
    for i in range(100):
        percentage = f"{i + 1}%"
        await page.set_content(
            f'<body style="box-sizing: border-box; width: 100%; height: 100%; margin:0; background: linear-gradient(to bottom, red {percentage}, transparent {percentage}); border: 50px solid blue"></body>'
        )
        await utils.rafraf(page)
    for _ in range(10):
        await utils.rafraf(page)
    await context.tracing.stop(path=tmp_path / "trace.zip")

    trace = parse_trace_raw(tmp_path / "trace.zip")
    frames = [e for e in trace.events if e["type"] == "screencast-frame"]

    # Check all frame sizes.
    for frame in frames:
        assert frame["width"] == width
        assert frame["height"] == height
        image = decode_image(trace.resources[frame["file"]])
        assert image.width == preview_width
        assert image.height == preview_height

    frame = frames[-1]  # pick last frame.
    data = decode_image(trace.resources[frame["file"]]).tobytes()
    assert len(data) == preview_width * preview_height * 4
    # center is red
    expect_red(
        data,
        preview_width * preview_height * 4 // 2 + preview_width * 4 // 2,
    )
    expect_blue(data, preview_width * 5 * 4 + preview_width * 4 // 2)  # top
    expect_blue(
        data, preview_width * (preview_height - 5) * 4 + preview_width * 4 // 2
    )  # bottom
    expect_blue(data, preview_width * preview_height * 4 // 2 + 5 * 4)  # left
    expect_blue(
        data,
        preview_width * preview_height * 4 // 2 + (preview_width - 5) * 4,
    )  # right


async def test_TR_024_should_include_interrupted_actions(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.EMPTY_PAGE)
    await page.set_content("<button>Click</button>")
    await run_in_background(page, lambda: page.click('"ClickNoButton"'))
    await context.tracing.stop(path=tmp_path / "trace.zip")
    await context.close()

    trace = parse_trace_raw(tmp_path / "trace.zip")
    assert """Click locator('text="ClickNoButton"')""" in trace.actions


async def test_TR_025_should_throw_when_starting_with_different_options(
    context: BrowserContext,
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    with pytest.raises(Error) as exc_info:
        await context.tracing.start(screenshots=False, snapshots=False)
    assert "Tracing has been already started" in exc_info.value.message


async def test_TR_026_should_throw_when_stopping_without_start(
    context: BrowserContext, tmp_path: Path
) -> None:
    with pytest.raises(Error) as exc_info:
        await context.tracing.stop(path=tmp_path / "trace.zip")
    assert "Must start tracing before stopping" in exc_info.value.message


async def test_TR_027_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    await context.tracing.stop()


async def test_TR_028_start_should_return_a_disposable_that_discards_the_trace(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    async with await context.tracing.start():
        await page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        await context.tracing.stop(path=tmp_path / "trace.zip")
    assert "Must start tracing before stopping" in exc_info.value.message


async def test_TR_029_start_chunk_should_return_a_disposable_that_discards_the_chunk(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start()
    async with await context.tracing.start_chunk():
        await page.goto(server.EMPTY_PAGE)
    with pytest.raises(Error) as exc_info:
        await context.tracing.stop_chunk(path=tmp_path / "trace.zip")
    assert "Must start tracing before stopping" in exc_info.value.message


async def test_TR_030_should_work_with_multiple_chunks(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    await page.goto(server.PREFIX + "/frames/frame.html")

    await context.tracing.start_chunk()
    await page.set_content("<button>Click</button>")
    await page.click('"Click"')
    await run_in_background(page, lambda: page.click('"ClickNoButton"', timeout=0))
    await page.evaluate("() => {}")
    await context.tracing.stop_chunk(path=tmp_path / "trace.zip")

    await context.tracing.start_chunk()
    await page.hover('"Click"')
    await context.tracing.stop_chunk(path=tmp_path / "trace2.zip")

    await context.tracing.start_chunk()
    await page.click('"Click"')
    await context.tracing.stop_chunk()  # Should stop without a path.

    trace1 = parse_trace_raw(tmp_path / "trace.zip")
    assert trace1.events[0]["type"] == "context-options"
    assert trace1.actions == [
        "Set content",
        """Click locator('text="Click"')""",
        """Click locator('text="ClickNoButton"')""",
        "Evaluate",
    ]
    assert any(e["type"] == "frame-snapshot" for e in trace1.events)
    assert resource_snapshot(trace1.events, "style.css")

    trace2 = parse_trace_raw(tmp_path / "trace2.zip")
    assert trace2.events[0]["type"] == "context-options"
    assert trace2.actions == [
        """Hover locator('text="Click"')""",
    ]
    assert any(e["type"] == "frame-snapshot" for e in trace2.events)
    assert resource_snapshot(trace2.events, "style.css")


async def test_TR_031_should_export_trace_concurrently_to_second_navigation(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    for timeout in range(0, 200, 20):
        await context.tracing.start(screenshots=True, snapshots=True)
        await page.goto(server.PREFIX + "/grid.html")

        # Navigate to the same page to produce the same trace resources
        # that might be concurrently exported.
        async def navigate() -> None:
            await page.goto(server.PREFIX + "/grid.html")

        async def wait_and_stop() -> None:
            await page.wait_for_timeout(timeout)
            await context.tracing.stop(path=tmp_path / "trace.zip")

        await asyncio.gather(navigate(), wait_and_stop())


async def test_TR_032_should_not_hang_for_clicks_that_open_dialogs(
    context: BrowserContext, page: Page
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    async with page.expect_event("dialog") as dialog_info:
        await page.set_content("<div onclick='window.alert(123)'>Click me</div>")
        try:
            await page.click("div", timeout=3500)
        except Error:
            pass
    dialog = await dialog_info.value
    await dialog.dismiss()
    await context.tracing.stop()


async def test_TR_033_should_ignore_iframes_in_head(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    await page.goto(server.PREFIX + "/input/button.html")
    await page.evaluate(
        """() => {
    document.head.appendChild(document.createElement('iframe'));
    // Add iframe in a shadow tree.
    const div = document.createElement('div');
    document.head.appendChild(div);
    const shadow = div.attachShadow({ mode: 'open' });
    shadow.appendChild(document.createElement('iframe'));
  }"""
    )

    await context.tracing.start(screenshots=True, snapshots=True)
    await page.click("button")
    await context.tracing.stop_chunk(path=tmp_path / "trace.zip")

    trace = parse_trace_raw(tmp_path / "trace.zip")
    assert trace.actions == ["Click locator('button')"]
    assert any(e["type"] == "frame-snapshot" for e in trace.events)
    assert not any(
        e["type"] == "frame-snapshot" and "IFRAME" in json.dumps(e["snapshot"]["html"])
        for e in trace.events
    )


@pytest.mark.xfail(
    reason="python: trace stacks keep the asyncio and pytest frames below the test (upstream keeps only the test's frames)",
    strict=True,
)
async def test_TR_034_should_hide_internal_stack_frames(
    context: BrowserContext, page: Page, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    eval_promise: List["asyncio.Future[Any]"] = []

    async def on_dialog(dialog: Dialog) -> None:
        eval_promise.append(await run_in_background(page, lambda: page.evaluate("2+2")))
        await dialog.dismiss()

    page.on("dialog", on_dialog)
    await page.set_content("<div onclick='window.alert(123)'>Click me</div>")
    await page.click("div")
    await eval_promise[0]
    trace_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_path)

    trace = parse_trace_raw(trace_path)
    actions = [a for a in trace.action_objects if a["class"] != "Tracing"]
    assert len(actions) == 4
    for action in actions:
        assert relative_stack(action, trace.stacks) == ["test_tracing.py"]


@pytest.mark.xfail(
    reason="python: trace stacks keep the asyncio and pytest frames below the test (upstream keeps only the test's frames)",
    strict=True,
)
async def test_TR_035_should_hide_internal_stack_frames_in_expect(
    context: BrowserContext, page: Page, tmp_path: Path
) -> None:
    await context.tracing.start(screenshots=True, snapshots=True)
    expect_promise: List["asyncio.Future[Any]"] = []

    async def on_dialog(dialog: Dialog) -> None:
        expect_promise.append(
            await run_in_background(page, lambda: expect(page).to_have_title("Hello"))
        )
        await dialog.dismiss()

    page.on("dialog", on_dialog)
    await page.set_content(
        "<title>Hello</title><div onclick='window.alert(123)'>Click me</div>"
    )
    await page.click("div")
    await expect(page.locator("div")).to_be_visible()
    assert await expect_promise[0] is None
    trace_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_path)

    trace = parse_trace_raw(trace_path)
    actions = [a for a in trace.action_objects if a["class"] != "Tracing"]
    assert len(actions) == 5
    for action in actions:
        assert relative_stack(action, trace.stacks) == ["test_tracing.py"]


async def test_TR_036_should_record_global_request_trace(
    playwright: Playwright, context: BrowserContext, server: Server, tmp_path: Path
) -> None:
    request = await playwright.request.new_context()
    await request.tracing.start(snapshots=True)
    url = server.PREFIX + "/simple.json"
    await request.get(url)
    trace_path = tmp_path / "trace.zip"
    await request.tracing.stop(path=trace_path)
    await request.dispose()

    trace = parse_trace_raw(trace_path)
    actions = [e for e in trace.events if e["type"] == "resource-snapshot"]
    assert len(actions) == 1
    assert actions[0]["snapshot"]["request"]["method"] == "GET"
    assert actions[0]["snapshot"]["request"]["url"] == url
    response = actions[0]["snapshot"]["response"]
    assert response["status"] == 200
    assert response["statusText"] == "OK"
    assert {"name": "Content-Length", "value": "15"} in [
        {"name": h["name"], "value": h["value"]} for h in response["headers"]
    ]


async def test_TR_037_should_store_global_request_traces_separately(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    request = await playwright.request.new_context()
    request2 = await playwright.request.new_context()
    await asyncio.gather(
        request.tracing.start(snapshots=True),
        request2.tracing.start(snapshots=True),
    )
    url = server.PREFIX + "/simple.json"
    await asyncio.gather(request.get(url), request2.post(url))
    trace_path = tmp_path / "trace.zip"
    trace2_path = tmp_path / "trace2.zip"
    await asyncio.gather(
        request.tracing.stop(path=trace_path),
        request2.tracing.stop(path=trace2_path),
    )
    await request.dispose()
    await request2.dispose()

    trace = parse_trace_raw(trace_path)
    actions = [e for e in trace.events if e["type"] == "resource-snapshot"]
    assert len(actions) == 1
    assert actions[0]["snapshot"]["request"]["method"] == "GET"
    assert actions[0]["snapshot"]["request"]["url"] == url

    trace = parse_trace_raw(trace2_path)
    actions = [e for e in trace.events if e["type"] == "resource-snapshot"]
    assert len(actions) == 1
    assert actions[0]["snapshot"]["request"]["method"] == "POST"
    assert actions[0]["snapshot"]["request"]["url"] == url


async def test_TR_038_should_store_post_data_for_global_request(
    playwright: Playwright, server: Server, tmp_path: Path
) -> None:
    request = await playwright.request.new_context()
    await request.tracing.start(snapshots=True)
    url = server.PREFIX + "/simple.json"
    await request.post(url, data="test")
    trace_path = tmp_path / "trace.zip"
    await request.tracing.stop(path=trace_path)
    await request.dispose()

    trace = parse_trace_raw(trace_path)
    actions = [e for e in trace.events if e["type"] == "resource-snapshot"]
    assert len(actions) == 1
    req = actions[0]["snapshot"]["request"]
    assert (req.get("postData") or {}).get("_file")
    assert req["method"] == "POST"
    assert req["url"] == url


async def test_TR_039_should_not_flush_console_events(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    # Upstream reads the traces dir that the test runner gives the browser.
    traces_dir = tmp_path / "traces"
    browser = await browser_type.launch(**launch_arguments, traces_dir=traces_dir)
    context = await browser.new_context()
    page = await context.new_page()
    test_id = "TR-039"
    await context.tracing.start(name=test_id)
    counter = 0

    def predicate(_: Any) -> bool:
        nonlocal counter
        counter += 1
        return counter == 100

    async with page.expect_event("console", predicate=predicate):
        await page.evaluate(
            """() => {
    window.builtins.setTimeout(() => {
      for (let i = 0; i < 100; ++i)
        console.log('hello ' + i);
    }, 10);
    return 31415926;
  }"""
        )

    def read_trace() -> str:
        trace_name = next(
            name for name in os.listdir(traces_dir) if name.endswith(test_id + ".trace")
        )
        return (traces_dir / trace_name).read_text()

    content = ""

    def check_result() -> None:
        nonlocal content
        content = read_trace()
        assert "31415926" in content

    await to_pass(page, check_result)
    assert "hello 0" not in content

    await page.evaluate("() => 42")

    def check_console() -> None:
        content = read_trace()
        assert "hello 0" in content
        assert "hello 99" in content

    await to_pass(page, check_console)
    await browser.close()


async def test_TR_040_should_flush_console_events_on_tracing_stop(
    context: BrowserContext, page: Page, tmp_path: Path
) -> None:
    await context.tracing.start()
    counter = 0

    def predicate(_: Any) -> bool:
        nonlocal counter
        counter += 1
        return counter == 100

    async with page.expect_event("console", predicate=predicate):
        await page.evaluate(
            """() => {
    window.builtins.setTimeout(() => {
      for (let i = 0; i < 100; ++i)
        console.log('hello ' + i);
    });
  }"""
        )
    trace_path = tmp_path / "trace.zip"
    await context.tracing.stop(path=trace_path)
    trace = parse_trace_raw(trace_path)
    events = [e for e in trace.events if e["type"] == "console"]
    assert len(events) == 100


@pytest.mark.xfail(
    reason="python: Waiter titles the wait 'Wait for event \"page.expect_event(console)\"' instead of 'Wait for event \"console\"'",
    strict=True,
)
async def test_TR_041_should_not_emit_after_w_o_before(
    browser_type: BrowserType, launch_arguments: Dict, tmp_path: Path
) -> None:
    traces_dir = tmp_path / "traces"
    browser = await browser_type.launch(**launch_arguments, traces_dir=traces_dir)
    context = await browser.new_context()
    page = await context.new_page()

    await context.tracing.start(name="name1", snapshots=True)
    evaluate_promise = await run_in_background(
        page,
        lambda: page.evaluate(
            """() => {
    console.log('started');
    return new Promise(f => window.callback = f);
  }"""
        ),
    )
    async with page.expect_event("console"):
        pass
    await context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert (traces_dir / "name1.trace").exists() is True

    await context.tracing.start_chunk(name="name2")
    await page.evaluate_handle("() => window.callback()")
    await evaluate_promise
    await context.tracing.stop(path=tmp_path / "trace2.zip")
    assert (traces_dir / "name2.trace").exists() is True

    await browser.close()
    min_call_id = 100000

    def sanitize(e: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal min_call_id
        if e["type"] == "after" or e["type"] == "before":
            min_call_id = min(min_call_id, int(e["callId"].split("@")[1]))
            result = {
                "type": e["type"],
                "callId": int(e["callId"].split("@")[1]) - min_call_id,
            }
            if e.get("title") is not None:
                result["title"] = e["title"]
            return result
        return None

    events = parse_trace_raw(tmp_path / "trace1.zip").events
    sanitized = [s for s in map(sanitize, events) if s]
    assert [{k: v for k, v in s.items() if k != "callId"} for s in sanitized] == [
        {"type": "before"},
        {"type": "before", "title": 'Wait for event "console"'},
        {"type": "after"},
    ]
    call1 = sanitized[0]["callId"]
    assert sanitized[1]["callId"] == sanitized[2]["callId"]

    events = parse_trace_raw(tmp_path / "trace2.zip").events
    sanitized = [s for s in map(sanitize, events) if s]
    assert [{k: v for k, v in s.items() if k != "callId"} for s in sanitized] == [
        {"type": "before"},
        {"type": "after"},
    ]
    call2before = sanitized[0]["callId"]
    call2after = sanitized[1]["callId"]
    assert call2before > call1
    assert call2after == call2before


async def test_TR_042_should_save_trace_while_a_web_socket_keeps_streaming_frames(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    streaming = [True]

    def on_connection(ws: WebSocketProtocol) -> None:
        def send() -> None:
            if streaming[0] and ws.state == WebSocketProtocol.STATE_OPEN:
                ws.sendMessage(b"x" * 16 * 1024)

        timer = LoopingCall(send)
        timer.start(0.001)

        def stop(*args: Any) -> None:
            if timer.running:
                timer.stop()

        ws.events.on("close", stop)

    server.once_web_socket_connection(on_connection)

    await context.tracing.start(snapshots=True)

    await context.tracing.start_chunk()
    await page.goto(server.EMPTY_PAGE)
    await page.evaluate(
        """url => {
    window.ws = new WebSocket(url);
    return new Promise(resolve => window.ws.addEventListener('open', () => resolve()));
  }""",
        f"ws://{server.HOST}/ws",
    )
    await page.wait_for_timeout(100)
    trace_path1 = tmp_path / "trace1.zip"
    await context.tracing.stop_chunk(path=trace_path1)

    streaming[0] = False
    await context.tracing.start_chunk()
    await page.wait_for_timeout(100)
    trace_path2 = tmp_path / "trace2.zip"
    await context.tracing.stop_chunk(path=trace_path2)

    await page.evaluate(
        """() => new Promise(resolve => {
    const ws = window.ws;
    if (ws.readyState === WebSocket.CLOSED) {
      resolve();
      return;
    }
    ws.addEventListener('close', () => resolve(), { once: true });
    ws.close();
  })"""
    )

    web_socket_lines = []
    for path in [trace_path1, trace_path2]:
        resources = parse_trace_raw(path).resources
        websocket_resource = next(
            (name, buffer)
            for name, buffer in resources.items()
            if name.endswith(".jsonl")
        )
        lines = [line for line in websocket_resource[1].decode().split("\n") if line]
        assert len(lines) > 0
        for line in lines:
            json.loads(line)
        web_socket_lines.append({"path": path, "lines": lines})
    assert web_socket_lines[0]["path"] != web_socket_lines[1]["path"]
    assert web_socket_lines[1]["lines"] == web_socket_lines[1]["lines"]
