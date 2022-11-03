# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
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

import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from playwright.sync_api import Browser, BrowserContext, Page
from tests.server import Server


def test_browser_context_output_trace(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    context.tracing.stop(path=tmp_path / "trace.zip")
    assert Path(tmp_path / "trace.zip").exists()


def test_browser_context_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    context.tracing.stop()


def test_browser_context_output_trace_chunk(
    browser: Browser, server: Server, tmp_path: Path
) -> None:
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(server.PREFIX + "/grid.html")
    button = page.locator(".box").first

    context.tracing.start_chunk(title="foo")
    button.click()
    context.tracing.stop_chunk(path=tmp_path / "trace1.zip")
    assert Path(tmp_path / "trace1.zip").exists()

    context.tracing.start_chunk(title="foo")
    button.click()
    context.tracing.stop_chunk(path=tmp_path / "trace2.zip")
    assert Path(tmp_path / "trace2.zip").exists()


def test_should_collect_sources(
    context: BrowserContext, page: Page, server: Server, tmp_path: Path
) -> None:
    context.tracing.start(sources=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click("button")
    path = tmp_path / "trace.zip"
    context.tracing.stop(path=path)

    (resources, events) = parse_trace(path)
    current_file_content = Path(__file__).read_bytes()
    found_current_file = False
    for name, resource in resources.items():
        if resource == current_file_content:
            found_current_file = True
            break
    assert found_current_file


def test_should_collect_trace_with_resources_but_no_js(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.PREFIX + "/frames/frame.html")
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    page.mouse.move(20, 20)
    page.mouse.dblclick(30, 30)
    page.keyboard.insert_text("abc")
    page.wait_for_timeout(2000)  # Give it some time to produce screenshots.
    page.route(
        "**/empty.html", lambda route: route.continue_()
    )  # should produce a route.continue_ entry.
    page.goto(server.EMPTY_PAGE)
    page.goto(
        server.PREFIX + "/one-style.html"
    )  # should not produce a route.continue_ entry since we continue all routes if no match.
    page.close()
    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert events[0]["type"] == "context-options"
    assert get_actions(events) == [
        "Page.goto",
        "Page.set_content",
        "Page.click",
        "Mouse.move",
        "Mouse.dblclick",
        "Keyboard.insert_text",
        "Page.wait_for_timeout",
        "Page.route",
        "Page.goto",
        "Route.continue_",
        "Page.goto",
        "Page.close",
        "Tracing.stop",
    ]

    assert len(list(filter(lambda e: e["type"] == "frame-snapshot", events))) >= 1
    assert len(list(filter(lambda e: e["type"] == "screencast-frame", events))) >= 1
    style = list(
        filter(
            lambda e: e["type"] == "resource-snapshot"
            and e["snapshot"]["request"]["url"].endswith("style.css"),
            events,
        )
    )[0]
    assert style
    assert style["snapshot"]["response"]["content"]["_sha1"]
    script = list(
        filter(
            lambda e: e["type"] == "resource-snapshot"
            and e["snapshot"]["request"]["url"].endswith("script.js"),
            events,
        )
    )[0]
    assert script
    assert script["snapshot"]["response"]["content"].get("_sha1") is None


def test_should_collect_two_traces(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    page.click('"Click"')
    tracing1_path = tmpdir / "trace1.zip"
    context.tracing.stop(path=tracing1_path)

    context.tracing.start(screenshots=True, snapshots=True)
    page.dblclick('"Click"')
    page.close()
    tracing2_path = tmpdir / "trace2.zip"
    context.tracing.stop(path=tracing2_path)

    (_, events) = parse_trace(tracing1_path)
    assert events[0]["type"] == "context-options"
    assert get_actions(events) == [
        "Page.goto",
        "Page.set_content",
        "Page.click",
        "Tracing.stop",
    ]

    (_, events) = parse_trace(tracing2_path)
    assert events[0]["type"] == "context-options"
    assert get_actions(events) == ["Page.dblclick", "Page.close", "Tracing.stop"]


def test_should_not_throw_when_stopping_without_start_but_not_exporting(
    context: BrowserContext,
) -> None:
    context.tracing.stop()


def test_should_work_with_playwright_context_managers(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)
    page.goto(server.EMPTY_PAGE)
    page.set_content("<button>Click</button>")
    with page.expect_console_message() as message_info:
        page.evaluate('() => console.log("hello")')
        page.click('"Click"')
    assert (message_info.value).text == "hello"

    with page.expect_popup():
        page.evaluate("window._popup = window.open(document.location.href)")
    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert events[0]["type"] == "context-options"
    assert get_actions(events) == [
        "Page.goto",
        "Page.set_content",
        "Page.expect_console_message",
        "Page.evaluate",
        "Page.click",
        "Page.expect_popup",
        "Page.evaluate",
        "Tracing.stop",
    ]


def test_should_display_wait_for_load_state_even_if_did_not_wait_for_it(
    context: BrowserContext, page: Page, server: Server, tmpdir: Path
) -> None:
    context.tracing.start(screenshots=True, snapshots=True)

    page.goto(server.EMPTY_PAGE)
    page.wait_for_load_state("load")
    page.wait_for_load_state("load")

    trace_file_path = tmpdir / "trace.zip"
    context.tracing.stop(path=trace_file_path)

    (_, events) = parse_trace(trace_file_path)
    assert get_actions(events) == [
        "Page.goto",
        "Page.wait_for_load_state",
        "Page.wait_for_load_state",
        "Tracing.stop",
    ]


def parse_trace(path: Path) -> Tuple[Dict[str, bytes], List[Any]]:
    resources: Dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as zip:
        for name in zip.namelist():
            resources[name] = zip.read(name)
    events: List[Any] = []
    for name in ["trace.trace", "trace.network"]:
        for line in resources[name].decode().splitlines():
            events.append(json.loads(line))
    return (resources, events)


def get_actions(events: List[Any]) -> List[str]:
    action_events = sorted(
        list(
            filter(
                lambda e: e["type"] == "action"
                and e["metadata"].get("internal", False) is False,
                events,
            )
        ),
        key=lambda e: e["metadata"]["startTime"],
    )
    return [e["metadata"]["apiName"] for e in action_events]
